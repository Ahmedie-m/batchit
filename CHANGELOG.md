# Changelog

All notable changes to this project will be documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] - 2026-03-30

### Fixed
- `async_batcher` now propagates exceptions raised by the source — previously they were silently swallowed

### Added
- `py.typed` marker (PEP 561) — mypy and pyright now use inline types
- Python 3.13 support — tested in CI and declared in classifiers
- `tests/test_kafka.py` — sync and async Kafka consumer pattern tests
- `tests/test_db.py` — database cursor and file iterator pattern tests
- `llms.txt` — structured API reference for AI coding assistants

### Changed
- Expanded PyPI classifiers and keywords for better discoverability
- CI now tests against Python 3.10, 3.11, 3.12, and 3.13

## [0.1.0] - 2026-03-30

### Added
- `batcher()` — batch any sync iterable by count, elapsed time, or both
- `async_batcher()` — batch any async iterable with real-time timeout support
- 30 tests covering size-only, timeout-only, and combined flush modes
