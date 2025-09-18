__all__ = ["reverse_enumerate", "split_every"]

import warnings
from collections.abc import Callable, Collection, Iterable, Iterator, Sequence
from itertools import islice
from typing import overload


def reverse_enumerate[T](lst: Sequence[T]) -> Iterator[tuple[int, T]]:
    """Like enumerate but in the other direction.

    Usage::

        >>> a = ['a', 'b', 'c']
        >>> list(reverse_enumerate(a))
        [(2, 'c'), (1, 'b'), (0, 'a')]
    """
    return zip(range(len(lst) - 1, -1, -1), reversed(lst), strict=False)


@overload
def split_every[T](n: int, iterable: Iterable[T]) -> Iterator[tuple[T, ...]]: ...


@overload
def split_every[T](
    n: int, iterable: Iterable[T], piece_maker: type[Collection[T]]
) -> Iterator[Collection[T]]: ...


@overload
def split_every[T, P](
    n: int, iterable: Iterable[T], piece_maker: Callable[[Iterable[T]], P]
) -> Iterator[P]: ...


def split_every[T](n: int, iterable: Iterable[T], piece_maker=tuple):
    """Splits an iterable into length-n pieces.

    .. deprecated:: 19.0
        Use :func:`itertools.batched` (Python 3.12+) instead.
        Note the swapped argument order: ``batched(iterable, n)`` vs ``split_every(n, iterable)``.

    The last piece will be shorter if ``n`` does not evenly divide
    the iterable length.

    :param int n: maximum size of each generated chunk
    :param Iterable iterable: iterable to chunk into pieces
    :param piece_maker: callable taking an iterable and collecting each
                        chunk from its slice, *must consume the entire slice*.

    Examples::

        >>> list(split_every(3, range(10)))
        [(0, 1, 2), (3, 4, 5), (6, 7, 8), (9,)]
        >>> list(split_every(3, range(10), list))
        [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]
    """
    warnings.warn(
        "split_every() is deprecated, use itertools.batched(iterable, n) instead. "
        "Note the swapped argument order.",
        DeprecationWarning,
        stacklevel=2,
    )
    iterator = iter(iterable)
    piece = piece_maker(islice(iterator, n))
    while piece:
        yield piece
        piece = piece_maker(islice(iterator, n))
