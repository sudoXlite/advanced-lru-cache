from __future__ import annotations

import asyncio
import functools
import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Dict, Hashable, Tuple, TypeVar, Awaitable

T = TypeVar("T")


def make_hashable(obj: Any) -> Hashable:
    if isinstance(obj, (str, bytes, int, float, bool, type(None))):
        return obj
    if isinstance(obj, tuple):
        return tuple(make_hashable(x) for x in obj)
    if isinstance(obj, (list, set, frozenset)):
        return tuple(sorted(make_hashable(x) for x in obj))
    if isinstance(obj, dict):
        return tuple(sorted((make_hashable(k), make_hashable(v)) for k, v in obj.items()))
    if hasattr(obj, "__dict__"):
        return make_hashable(vars(obj))
    return repr(obj)


class AdvancedLRUCache:
    """
    Production-grade LRU cache engine.

    - Sync & async APIs
    - Thread-safe & asyncio-safe
    - LRU eviction
    - Optional TTL
    - Async single-flight
    - Key-level invalidation
    """

    def __init__(self, maxsize: int = 128, ttl: float | None = None) -> None:
        if maxsize <= 0:
            raise ValueError("maxsize must be > 0")

        self.maxsize = maxsize
        self.ttl = ttl

        self._cache: OrderedDict[Hashable, Tuple[Any, float]] = OrderedDict()
        self._inflight: Dict[Hashable, asyncio.Future] = {}

        # One lock per concurrency model, both protect inflight
        self._lock = threading.RLock()
        self._async_lock = asyncio.Lock()

        self.hits = 0
        self.misses = 0

    # -------------------------
    # INTERNAL
    # -------------------------

    def _make_key(self, args: tuple, kwargs: dict) -> Hashable:
        return (make_hashable(args), make_hashable(kwargs))

    def _expired(self, ts: float, now: float) -> bool:
        return self.ttl is not None and (now - ts) >= self.ttl

    # -------------------------
    # SYNC API
    # -------------------------

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        key = self._make_key(args, kwargs)

        with self._lock:
            now = time.monotonic()
            if key in self._cache:
                value, ts = self._cache[key]
                if not self._expired(ts, now):
                    self._cache.move_to_end(key)
                    self.hits += 1
                    return value
                del self._cache[key]
            self.misses += 1

        result = func(*args, **kwargs)

        with self._lock:
            self._cache[key] = (result, time.monotonic())
            self._cache.move_to_end(key)
            if len(self._cache) > self.maxsize:
                self._cache.popitem(last=False)

        return result

    # -------------------------
    # ASYNC API (SINGLE-FLIGHT)
    # -------------------------

    async def call_async(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        key = self._make_key(args, kwargs)

        async with self._async_lock:
            now = time.monotonic()
            if key in self._cache:
                value, ts = self._cache[key]
                if not self._expired(ts, now):
                    self._cache.move_to_end(key)
                    self.hits += 1
                    return value
                del self._cache[key]

            if key in self._inflight:
                return await self._inflight[key]

            self.misses += 1
            fut = asyncio.get_running_loop().create_future()
            self._inflight[key] = fut

        try:
            result = await func(*args, **kwargs)
        except Exception as exc:
            async with self._async_lock:
                self._inflight.pop(key).set_exception(exc)
            raise

        async with self._async_lock:
            self._cache[key] = (result, time.monotonic())
            self._cache.move_to_end(key)
            if len(self._cache) > self.maxsize:
                self._cache.popitem(last=False)
            self._inflight.pop(key).set_result(result)

        return result

    # -------------------------
    # DECORATORS
    # -------------------------

    def sync(self, func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return self.call(func, *args, **kwargs)
        return wrapper

    def async_cache(self, func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await self.call_async(func, *args, **kwargs)
        return wrapper

    # -------------------------
    # MANAGEMENT
    # -------------------------

    def invalidate(self, *args: Any, **kwargs: Any) -> None:
        key = self._make_key(args, kwargs)
        with self._lock:
            self._cache.pop(key, None)

    async def invalidate_async(self, *args: Any, **kwargs: Any) -> None:
        key = self._make_key(args, kwargs)
        async with self._async_lock:
            self._cache.pop(key, None)
            fut = self._inflight.pop(key, None)
            if fut and not fut.done():
                fut.cancel()

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self.hits = 0
            self.misses = 0

        # cancel inflight safely
        async def _cancel():
            async with self._async_lock:
                for fut in self._inflight.values():
                    if not fut.done():
                        fut.cancel()
                self._inflight.clear()

        try:
            asyncio.create_task(_cancel())
        except RuntimeError:
            pass

    def info(self) -> Dict[str, Any]:
        with self._lock:
            inflight = len(self._inflight)
            return {
                "hits": self.hits,
                "misses": self.misses,
                "size": len(self._cache),
                "maxsize": self.maxsize,
                "ttl": self.ttl,
                "inflight": inflight,
                        }
