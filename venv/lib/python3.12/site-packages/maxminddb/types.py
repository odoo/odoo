"""Types representing database records."""

from typing import AnyStr, Union

Primitive = Union[AnyStr, bool, float, int]
Record = Union[Primitive, "RecordList", "RecordDict"]


class RecordList(list[Record]):  # pylint: disable=too-few-public-methods
    """RecordList is a type for lists in a database record."""


class RecordDict(dict[str, Record]):  # pylint: disable=too-few-public-methods
    """RecordDict is a type for dicts in a database record."""
