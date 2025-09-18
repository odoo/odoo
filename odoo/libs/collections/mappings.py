__all__ = ["ConstantMapping", "DotDict", "ReadonlyDict", "submap"]

from collections.abc import Iterable, Mapping
from typing import Any


class ConstantMapping[T](Mapping[Any, T]):
    """An immutable mapping returning the provided value for every single key.

    Useful for default value to methods.

    Example::

        >>> m = ConstantMapping(42)
        >>> m['anything']
        42
        >>> m['something_else']
        42
    """

    __slots__ = ["_value"]

    def __init__(self, val: T):
        self._value = val

    def __len__(self):
        return 0

    def __iter__(self):
        return iter(())

    def __getitem__(self, item) -> T:
        return self._value


class ReadonlyDict[K, T](Mapping[K, T]):
    """Helper for an unmodifiable dictionary, not even updatable using `dict.update`.

    This is similar to a `frozendict`, with one drawback and one advantage:

    - `dict.update` works for a `frozendict` but not for a `ReadonlyDict`.
    - `json.dumps` works for a `frozendict` by default but not for a `ReadonlyDict`.

    This comes from the fact `frozendict` inherits from `dict`
    while `ReadonlyDict` inherits from `collections.abc.Mapping`.

    So, depending on your needs,
    whether you absolutely must prevent the dictionary from being updated (e.g., for security reasons)
    or you require it to be supported by `json.dumps`, you can choose either option.

    Example::

        >>> data = ReadonlyDict({'foo': 'bar'})
        >>> data['baz'] = 'xyz'  # raises TypeError
        >>> data.update({'baz': 'xyz'})  # raises AttributeError
        >>> dict.update(data, {'baz': 'xyz'})  # raises TypeError
    """

    __slots__ = ("_data__",)

    def __init__(self, data):
        self._data__ = dict(data)

    def __contains__(self, key: K):
        return key in self._data__

    def __getitem__(self, key: K) -> T:
        return self._data__[key]

    def __len__(self):
        return len(self._data__)

    def __iter__(self):
        return iter(self._data__)


def submap[K, T](mapping: Mapping[K, T], keys: Iterable[K]) -> Mapping[K, T]:
    """Get a filtered copy of the mapping where only some keys are present.

    :param mapping: The original dict-like structure to filter
    :param keys: The list of keys to keep
    :returns: A filtered dict copy of the original mapping

    Example::

        >>> submap({'a': 1, 'b': 2, 'c': 3}, ['a', 'c'])
        {'a': 1, 'c': 3}
        >>> submap({'x': 10, 'y': 20}, ['y', 'z'])
        {'y': 20}
    """
    keys = frozenset(keys)
    return {key: mapping[key] for key in mapping if key in keys}


class DotDict(dict):
    """Helper for dot.notation access to dictionary attributes.

    Example::

        >>> foo = DotDict({'bar': False, 'nested': {'value': 42}})
        >>> foo.bar
        False
        >>> foo.nested.value
        42
    """

    def __getattr__(self, attrib):
        val = self.get(attrib)
        return DotDict(val) if isinstance(val, dict) else val
