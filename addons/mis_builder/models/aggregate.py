# Copyright 2014 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


def _sum(lst):
    """Same as stdlib sum but returns None instead of 0
    in case of empty sequence.

    >>> sum([1])
    1
    >>> _sum([1])
    1
    >>> sum([1, 2])
    3
    >>> _sum([1, 2])
    3
    >>> sum([])
    0
    >>> _sum([])
    """
    if not lst:
        return None
    return sum(lst)


def _avg(lst):
    """Arithmetic mean of a sequence. Returns None in case of empty sequence.

    >>> _avg([1])
    1.0
    >>> _avg([1, 2])
    1.5
    >>> _avg([])
    """
    if not lst:
        return None
    return sum(lst) / float(len(lst))


def _min(*args):
    """Same as stdlib min but returns None instead of exception
    in case of empty sequence.

    >>> min(1, 2)
    1
    >>> _min(1, 2)
    1
    >>> min([1, 2])
    1
    >>> _min([1, 2])
    1
    >>> min(1)
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
    TypeError: 'int' object is not iterable
    >>> _min(1)
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
    TypeError: 'int' object is not iterable
    >>> min([1])
    1
    >>> _min([1])
    1
    >>> min()
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
    TypeError: min expected 1 arguments, got 0
    >>> _min()
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
    TypeError: min expected 1 arguments, got 0
    >>> min([])
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
    ValueError: min() arg is an empty sequence
    >>> _min([])
    """
    if len(args) == 1 and not args[0]:
        return None
    return min(*args)


def _max(*args):
    """Same as stdlib max but returns None instead of exception
    in case of empty sequence.

    >>> max(1, 2)
    2
    >>> _max(1, 2)
    2
    >>> max([1, 2])
    2
    >>> _max([1, 2])
    2
    >>> max(1)
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
    TypeError: 'int' object is not iterable
    >>> _max(1)
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
    TypeError: 'int' object is not iterable
    >>> max([1])
    1
    >>> _max([1])
    1
    >>> max()
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
    TypeError: max expected 1 arguments, got 0
    >>> _max()
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
    TypeError: max expected 1 arguments, got 0
    >>> max([])
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
    ValueError: max() arg is an empty sequence
    >>> _max([])
    """
    if len(args) == 1 and not args[0]:
        return None
    return max(*args)


if __name__ == "__main__":  # pragma: no cover
    import doctest

    doctest.testmod()
