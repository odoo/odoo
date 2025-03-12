from builtins import bytes, str, zip
from itertools import tee, islice, chain
from typing import Any, Generator, Iterable, Iterator, List, Optional, Tuple, TypeVar

T = TypeVar("T")


def from_base(digits: List[int], base: int) -> int:
    return sum(v * (base ** (len(digits) - k - 1)) for k, v in enumerate(digits))


def to_base(value: int, base: int) -> List[int]:
    digits: List[int] = []

    while value > 0:
        digits.insert(0, value % base)
        value //= base

    return digits


def switch_base(digits: List[int], source_base: int, target_base: int) -> List[int]:
    return to_base(from_base(digits, source_base), target_base)


def chunks(iterable: Iterable[T], size: int) -> Generator[Tuple[T, ...], None, None]:
    """Generator which chunks data into chunks of given size."""
    it = iter(iterable)
    while True:
        chunk = tuple(islice(it, size))
        if not chunk:
            return
        yield chunk


def to_bytes(input: Any, encoding: str = "utf-8") -> bytes:
    if isinstance(input, bytes):
        return input

    if isinstance(input, str):
        return bytes(input, encoding)

    raise ValueError("Invalid input, expected string or bytes")


def iterate_prev_next(iterable: Iterable[T]) -> Iterator[Tuple[Optional[T], T, Optional[T]]]:
    """
    Creates an iterator which provides previous, current and next item.
    """
    prevs, items, nexts = tee(iterable, 3)
    prevs = chain([None], prevs)
    nexts = chain(islice(nexts, 1, None), [None])
    return zip(prevs, items, nexts)
