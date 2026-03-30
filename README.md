# batchit

[![PyPI version](https://img.shields.io/pypi/v/batchit.svg)](https://pypi.org/project/batchit/)
[![Python versions](https://img.shields.io/pypi/pyversions/batchit.svg)](https://pypi.org/project/batchit/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![CI](https://github.com/Ahmedie-m/batchit/actions/workflows/ci.yml/badge.svg)](https://github.com/Ahmedie-m/batchit/actions/workflows/ci.yml)

Batch any Python iterator by **count**, **elapsed time**, or both.

```python
from batchit import batcher

for batch in batcher(source, size=100, timeout=5.0):
    db.bulk_insert(batch)   # never waits more than 5 s; never more than 100 items
```

## Why batchit?

`more-itertools.batched()` batches by count only.  In real streaming workloads
(Kafka consumers, database cursors, API result streams) you also need a **time
window**: flush whatever you have after *N* seconds, even if the count hasn't
been reached yet.  Every team writes this boilerplate from scratch.  `batchit`
is that one `pip install` away.

| | Count limit | Time limit | Async | Dependencies |
|---|:---:|:---:|:---:|:---:|
| `batchit` | ✓ | ✓ | ✓ | none |
| `more-itertools` | ✓ | ✗ | ✗ | 1 |
| `toolz` | ✓ | ✗ | ✗ | 1 |
| hand-rolled | maybe | maybe | maybe | — |

## Installation

```bash
pip install batchit
```

No runtime dependencies.  Python 3.10–3.13.  Fully typed (PEP 561).

## Usage

### Sync — `batcher`

```python
from batchit import batcher

# By size only
for batch in batcher(range(1000), size=50):
    process(batch)

# By timeout only (flush every 5 seconds)
for batch in batcher(kafka_consumer, timeout=5.0):
    send_to_api(batch)

# By both — whichever fires first
for batch in batcher(db_cursor, size=200, timeout=10.0):
    write_to_s3(batch)
```

### Async — `async_batcher`

```python
from batchit import async_batcher

async for batch in async_batcher(async_source, size=100, timeout=5.0):
    await db.bulk_insert(batch)
```

## Timeout semantics

The two variants behave differently under a slow or stalled source — know which you need:

| | `batcher` (sync) | `async_batcher` (async) |
|---|---|---|
| **How timeout fires** | Checked on each item arrival | Fires independently via `asyncio.wait_for` |
| **Stalled source** | Waits until the next item arrives, then flushes | Flushes after *T* seconds even with no new items |
| **Triggering item** | Included in the flushing batch | Starts the next batch |
| **Threading** | None — single-threaded safe | asyncio event loop only |
| **Source exception** | Propagates immediately | Propagates to consumer |

**Rule of thumb:** use `batcher` for sync iterables where the source drives timing (Kafka poll loops, DB cursors). Use `async_batcher` when you need the timeout to fire independently of item delivery (WebSocket streams, async queues, idle-timeout flushing).

## API

### `batcher(iterable, *, size=None, timeout=None)`

| Parameter | Type | Description |
|-----------|------|-------------|
| `iterable` | `Iterable[T]` | Any iterable to batch |
| `size` | `int \| None` | Max items per batch |
| `timeout` | `float \| None` | Max seconds per batch, measured from the first item |

Yields `list[T]`.  At least one of `size` / `timeout` must be provided.
Remaining items are always yielded — nothing is silently dropped.

### `async_batcher(aiterable, *, size=None, timeout=None, maxsize=0)`

Same parameters as `batcher`, plus:

| Parameter | Type | Description |
|-----------|------|-------------|
| `aiterable` | `AsyncIterable[T]` | Any async iterable to batch |
| `maxsize` | `int` | Max items to buffer internally before the producer blocks. `0` = unbounded (default) |

Accepts `AsyncIterable[T]`, yields `list[T]` asynchronously.  Set `maxsize` to apply
backpressure when the source can outpace the consumer.

## Patterns

### Kafka consumer

```python
from kafka import KafkaConsumer
from batchit import batcher

consumer = KafkaConsumer("events")
for batch in batcher(consumer, size=500, timeout=10.0):
    db.bulk_insert([msg.value for msg in batch])
    consumer.commit()
```

### Database cursor

```python
cursor.execute("SELECT * FROM events")
for batch in batcher(cursor, size=1000):
    warehouse.insert_many(batch)
```

### Async HTTP / WebSocket stream

```python
async for batch in async_batcher(response.content, size=64, timeout=2.0):
    await storage.write(batch)
```

### Backpressure — bounded queue

If your source can produce faster than the consumer processes, the internal queue
grows without bound.  Use `maxsize` to cap it — the producer will block naturally
when the queue is full:

```python
# Source blocked if more than 200 items are waiting to be batched
async for batch in async_batcher(fast_source(), size=50, timeout=2.0, maxsize=200):
    await slow_downstream(batch)
```

### AI / ML pipelines

Batch embedding requests to stay within API rate limits and maximise throughput:

```python
from batchit import async_batcher

async for batch in async_batcher(document_stream(), size=96, timeout=2.0):
    embeddings = await embed(batch)          # one API call per batch
    await vector_db.upsert(embeddings)
```

Batch LLM inference over a large dataset:

```python
from batchit import batcher

for batch in batcher(prompts, size=20):
    responses = llm.generate(batch)          # single batched call
    results.extend(responses)
```

Stream model outputs to a downstream consumer without accumulating everything in memory:

```python
async for batch in async_batcher(model.stream_predict(inputs), size=50, timeout=1.0):
    await sink.write(batch)
```

## Tests

The test suite is organised by use case:

| File | What it covers |
|---|---|
| `tests/test_sync.py` | Core sync batcher behaviour |
| `tests/test_async.py` | Core async batcher behaviour |
| `tests/test_kafka.py` | Kafka consumer patterns (sync + async) |
| `tests/test_db.py` | Database cursor and file iterator patterns |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
