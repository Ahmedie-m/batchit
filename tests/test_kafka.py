"""Kafka consumer patterns — sync and async.

These tests simulate the primary use case that motivated batchit: a Kafka
consumer that must flush a batch every N items *or* every T seconds, whichever
comes first.

Key behavioural difference between sync and async:
- Sync batcher: timeout is checked on item arrival only.  A pause in the
  source extends the current batch until the next item arrives.
- Async batcher: timeout fires independently via asyncio.wait_for, so a
  quiet broker still triggers a flush after T seconds.
"""

import asyncio
import time

import pytest

from batchit import async_batcher, batcher


# ---------------------------------------------------------------------------
# sync
# ---------------------------------------------------------------------------

def test_sync_burst_then_pause():
    """Burst of items, broker goes quiet, then a second burst.

    The first item after the pause triggers the flush because the timeout
    is checked after appending — so it lands in the first (timed-out) batch.
    """
    def kafka_consumer():
        for i in range(3):      # fast burst — items arrive within one poll
            yield i
        time.sleep(0.2)         # broker quiet — no messages for 200 ms
        for i in range(3, 5):   # second burst
            yield i

    result = list(batcher(kafka_consumer(), size=10, timeout=0.1))
    assert result == [[0, 1, 2, 3], [4]]
    assert sum(len(b) for b in result) == 5


def test_sync_size_fires_before_timeout():
    """When messages arrive fast, the size limit drives flushing."""
    def fast_consumer():
        yield from range(9)

    result = list(batcher(fast_consumer(), size=3, timeout=10.0))
    assert result == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]


def test_sync_commit_after_each_batch():
    """Simulate consumer.commit() after processing each batch — nothing lost."""
    committed: list[list[int]] = []

    def kafka_consumer():
        yield from range(7)

    for batch in batcher(kafka_consumer(), size=3, timeout=5.0):
        committed.append(batch)

    assert committed == [[0, 1, 2], [3, 4, 5], [6]]
    assert [item for batch in committed for item in batch] == list(range(7))


# ---------------------------------------------------------------------------
# async
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_async_burst_then_pause():
    """Async consumer: burst, then broker goes quiet longer than the timeout.

    Unlike the sync variant, the async batcher flushes *before* the next item
    arrives — timeout fires independently of item delivery.
    """
    async def kafka_consumer():
        for i in range(3):              # fast burst
            yield i
        await asyncio.sleep(0.2)        # broker quiet — longer than timeout
        for i in range(3, 5):           # second burst
            yield i

    result = [b async for b in async_batcher(kafka_consumer(), size=10, timeout=0.1)]
    assert result == [[0, 1, 2], [3, 4]]
    assert sum(len(b) for b in result) == 5


@pytest.mark.asyncio
async def test_async_size_fires_before_timeout():
    """When messages arrive fast, the size limit drives flushing."""
    async def fast_consumer():
        for i in range(9):
            yield i

    result = [b async for b in async_batcher(fast_consumer(), size=3, timeout=10.0)]
    assert result == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]


@pytest.mark.asyncio
async def test_async_commit_after_each_batch():
    """Simulate async consumer.commit() after processing each batch."""
    committed: list[list[int]] = []

    async def kafka_consumer():
        for i in range(7):
            yield i

    async for batch in async_batcher(kafka_consumer(), size=3, timeout=5.0):
        committed.append(batch)

    assert committed == [[0, 1, 2], [3, 4, 5], [6]]
    assert [item for batch in committed for item in batch] == list(range(7))
