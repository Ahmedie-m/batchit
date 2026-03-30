"""Database and file patterns — sync.

These tests simulate cursor-based bulk loading and file processing, the second
major use case for batchit after Kafka consumers.
"""

from io import StringIO

import pytest

from batchit import batcher


# ---------------------------------------------------------------------------
# database cursor simulation
# ---------------------------------------------------------------------------

class FakeCursor:
    """Minimal simulation of a DB-API 2.0 cursor iterator."""

    def __init__(self, rows: list) -> None:
        self._rows = rows

    def __iter__(self):
        yield from self._rows


def test_cursor_bulk_insert():
    """Batch a database cursor into fixed-size chunks for bulk insert."""
    rows = list(range(250))
    cursor = FakeCursor(rows)

    batches = list(batcher(cursor, size=100))

    assert len(batches) == 3                    # 100 + 100 + 50
    assert len(batches[0]) == 100
    assert len(batches[1]) == 100
    assert len(batches[2]) == 50
    assert [r for batch in batches for r in batch] == rows


def test_cursor_nothing_dropped():
    """Every row from the cursor ends up in exactly one batch."""
    rows = list(range(1337))
    batches = list(batcher(FakeCursor(rows), size=100))
    assert [r for batch in batches for r in batch] == rows


def test_cursor_smaller_than_batch_size():
    """A cursor with fewer rows than the batch size yields a single batch."""
    rows = [{"id": i} for i in range(10)]
    result = list(batcher(FakeCursor(rows), size=500))
    assert result == [rows]


def test_cursor_with_timeout():
    """Timeout-based flushing works with a cursor (e.g. slow remote DB)."""
    rows = list(range(20))
    batches = list(batcher(FakeCursor(rows), size=1000, timeout=5.0))
    # All rows arrive fast — one batch
    assert batches == [rows]


# ---------------------------------------------------------------------------
# file-like iterables
# ---------------------------------------------------------------------------

def test_file_lines_chunked():
    """Batch lines from a file (or StringIO) in chunks for bulk processing."""
    content = "\n".join(f"line{i}" for i in range(10))
    batches = list(batcher(StringIO(content), size=3))

    assert len(batches) == 4                    # 3 + 3 + 3 + 1
    assert sum(len(b) for b in batches) == 10


def test_file_single_batch():
    """When file is smaller than batch size, one batch is yielded."""
    content = "a\nb\nc"
    result = list(batcher(StringIO(content), size=100))
    assert len(result) == 1
    assert sum(len(b) for b in result) == 3
