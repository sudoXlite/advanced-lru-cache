# AdvancedLRUCache

**Production-grade LRU Cache Engine for Python**

A high-performance, feature-rich caching solution designed for real-world applications. It combines the best of synchronous and asynchronous caching with advanced features not found in standard libraries like `functools.lru_cache` or third-party packages.

## Features

- Full **synchronous** and **asynchronous** support
- **Thread-safe** (using `threading.RLock`) and **asyncio-safe** (using `asyncio.Lock`)
- **LRU (Least Recently Used)** eviction policy with O(1) operations
- Optional **TTL (Time-To-Live)** per entry
- **Async single-flight** deduplication – prevents duplicate concurrent computations
- Full support for **unhashable arguments** (lists, dicts, sets, nested structures, custom objects)
- **Key-level invalidation** (both sync and async)
- Detailed **cache statistics** (hits, misses, size, inflight, etc.)
- Clean, well-documented API with proper function name preservation (`functools.wraps`)

## Installation

This package is not yet on PyPI. To use it:

1. Clone the repository:
   ```bash
   git clone https://github.com/sudoXlite/advanced-lru-cache.git
   cd advanced-lru-cache
   ```

2. Install in development mode:
   ```bash
   pip install -e .
   ```

Or simply copy `advanced_lru_cache.py` into your project.

**Requirements**: Python 3.9+

No external dependencies.

## Usage

### Basic Setup

```python
from advanced_lru_cache import AdvancedLRUCache

# Create a cache instance
cache = AdvancedLRUCache(maxsize=128, ttl=300)  # Optional: 5-minute TTL
```

### Synchronous Usage

```python
@cache.sync
def expensive_calculation(n):
    print(f"Computing heavy task for {n}...")
    time.sleep(1)  # Simulate expensive work
    return n ** n

# First call — computes
print(expensive_calculation(10))

# Second call — returns from cache (no print)
print(expensive_calculation(10))

# Different argument — computes again
print(expensive_calculation(8))
```

### Asynchronous Usage

```python
import asyncio

@cache.async_cache
async def fetch_user_data(user_id):
    print(f"Fetching data for user {user_id} from API...")
    await asyncio.sleep(2)  # Simulate network delay
    return {"id": user_id, "name": "John Doe", "premium": True}

async def main():
    # First call — fetches
    print(await fetch_user_data(123))
    
    # Second call — instant cache hit
    print(await fetch_user_data(123))
    
    # Multiple concurrent calls — only one actual computation (single-flight)
    tasks = [fetch_user_data(456) for _ in range(5)]
    results = await asyncio.gather(*tasks)
    print("All 5 tasks completed — only one API call was made!")

asyncio.run(main())
```

### Working with Complex Arguments

The cache automatically handles unhashable types:

```python
@cache.sync
def process_data(items: list, config: dict):
    print("Processing complex data...")
    return sum(items) * len(config)

process_data([1, 2, 3], {"mode": "fast", "debug": True})  # Computes
process_data([1, 2, 3], {"mode": "fast", "debug": True})  # Cache hit!
```

### Cache Management

```python
# Get statistics
print(cache.info())
# Example output:
# {
#   'hits': 15,
#   'misses': 8,
#   'size': 23,
#   'maxsize': 128,
#   'ttl': 300,
#   'inflight': 0
# }

# Invalidate specific entry
cache.invalidate([1, 2, 3], {"mode": "fast"})
await cache.invalidate_async(user_id=123)  # Async version

# Clear entire cache
cache.clear()
```

## Comparison with Other Libraries

| Feature                        | functools.lru_cache | cachetools | aiocache       | **AdvancedLRUCache** |
|-------------------------------|---------------------|------------|----------------|----------------------|
| Sync support                  | Yes                 | Yes        | Partial        | Yes                  |
| Async support                 | No                  | No         | Yes            | Yes                  |
| Unhashable arguments          | No                  | No         | Partial        | Yes                  |
| TTL support                   | No                  | Some       | Yes            | Yes                  |
| Single-flight (async)         | No                  | No         | No             | Yes                  |
| Thread-safe                   | Partial             | Yes        | Partial        | Yes                  |
| Key-level invalidation        | No                  | Partial    | Partial        | Yes (sync & async)   |
| Detailed stats & management   | Basic               | Partial    | Partial        | Full                 |

## License

**All rights reserved.**

Copyright © 2026 [sudoXlite](https://github.com/sudoXlite)

You are permitted to:
- View and study the code
- Use this code (as-is or modified) in your own private or commercial projects
- Copy portions into your own work

Provided that this copyright notice remains intact.

**Redistribution in any form is strictly prohibited**, including:
- Publishing this code (modified or unmodified) under a different name
- Selling or distributing this code as a standalone product
- Creating public forks or derivative works that claim original authorship

For any other use, please contact the author.

See the [LICENSE](LICENSE) file for full terms.

---

**Author**: [PythonDev](https://t.me/PythonDev_WWW)
**Inspired by**: Real-world production needs and advanced Python concurrency patterns.

If you found this useful in your project — consider giving a ⭐ star! It means a lot.

Thank you for respecting the license. Happy coding! 🚀
