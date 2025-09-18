__all__ = ["groupby", "partition", "unique"]

from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator


def groupby[T, K](
    iterable: Iterable[T], key: Callable[[T], K] = lambda arg: arg
) -> Iterable[tuple[K, list[T]]]:
    """Return a collection of pairs ``(key, elements)`` from ``iterable``.

    The ``key`` is a function computing a key value for each element. This
    function is similar to ``itertools.groupby``, but aggregates all
    elements under the same key, not only consecutive elements.
    """
    groups: defaultdict[K, list[T]] = defaultdict(list)
    for elem in iterable:
        groups[key(elem)].append(elem)
    return groups.items()


def unique[T](it: Iterable[T]) -> Iterator[T]:
    """ "Uniquifier" for the provided iterable: will output each element of
    the iterable once.

    The iterable's elements must be hashable.

    :param Iterable it: The iterable to uniquify
    :rtype: Iterator
    """
    seen: set[T] = set()
    for e in it:
        if e not in seen:
            seen.add(e)
            yield e


def partition[T](pred: Callable[[T], bool], elems: Iterable[T]) -> tuple[list[T], list[T]]:
    """Partition elements into two lists based on a predicate.

    Return a pair equivalent to:
    ``filter(pred, elems), filter(lambda x: not pred(x), elems)``

    :param pred: Predicate function returning True/False
    :param elems: Iterable of elements to partition
    :returns: Tuple of (matching_elements, non_matching_elements)
    """
    yes: list[T] = []
    nos: list[T] = []
    for elem in elems:
        (yes if pred(elem) else nos).append(elem)
    return yes, nos
