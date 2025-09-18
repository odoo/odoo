"""
Shared ORM helper functions.

Multi-consumer utilities that are used across several ORM modules.
These are kept at the orm/ level to avoid circular imports between
the models and fields layers.
"""

import typing
from operator import itemgetter

from odoo.tools import SQL

if typing.TYPE_CHECKING:
    from .models.base import BaseModel


# =============================================================================
# ID Utilities
# =============================================================================


def _origin_ids_python(ids):
    """Extract origin IDs from any iterable of record IDs (pure Python)."""
    return [oid for id_ in ids if (oid := id_ or getattr(id_, "origin", None))]


try:
    from odoo_rust import origin_ids as _origin_ids_rust  # type: ignore[import-untyped]

    def _origin_ids(ids):
        """Extract origin IDs — Rust fast path for tuples, Python fallback."""
        if isinstance(ids, tuple):
            return _origin_ids_rust(ids)
        return _origin_ids_python(ids)

except ImportError:
    _origin_ids = _origin_ids_python


class OriginIds:
    """A reversible iterable returning the origin ids of a collection of ``ids``.

    Actual ids are returned as is, and ids without origin are not returned.
    This is useful for handling NewId objects that may have an origin reference.

    For eager consumption, prefer ``_origin_ids(ids)`` which uses Rust when
    available (~3x faster for int-only tuples).
    """

    __slots__ = ["ids"]

    def __init__(self, ids):
        self.ids = ids

    def __iter__(self):
        return iter(_origin_ids(self.ids))

    def __reversed__(self):
        for id_ in reversed(self.ids):
            if id_ := id_ or getattr(id_, "origin", None):
                yield id_


# =============================================================================
# Record Utilities
# =============================================================================


def itemgetter_tuple(items):
    """Create an itemgetter that always returns a tuple.

    Fixes itemgetter inconsistency of not returning a tuple if len(items) == 1:
    this function always returns an n-tuple where n = len(items).

    Args:
        items: Sequence of keys to get from an object.

    Returns:
        A callable that returns a tuple of values.

    Examples:
        >>> getter = itemgetter_tuple(['a'])
        >>> getter({'a': 1, 'b': 2})
        (1,)
        >>> getter = itemgetter_tuple(['a', 'b'])
        >>> getter({'a': 1, 'b': 2})
        (1, 2)
    """
    if len(items) == 0:
        return lambda a: ()
    if len(items) == 1:
        return lambda gettable: (gettable[items[0]],)
    return itemgetter(*items)


def to_record_ids(arg) -> list[int]:
    """Return the record ids of ``arg``.

    Args:
        arg: May be a recordset, an integer, or a list of integers.

    Returns:
        List of non-zero integer IDs.

    Examples:
        >>> to_record_ids(5)
        [5]
        >>> to_record_ids([1, 2, 0, 3])
        [1, 2, 3]
    """
    # Import here to avoid circular imports
    from .models.base import BaseModel

    if isinstance(arg, BaseModel):
        return arg.ids
    elif isinstance(arg, int):
        return [arg] if arg else []
    else:
        return [id_ for id_ in arg if id_]


def get_columns_from_sql_diagnostics(
    cr, diagnostics, *, check_registry=False
) -> list[str]:
    """Given the diagnostics of an error, return the affected column names by the constraint.

    This is useful for providing better error messages when database constraints fail.

    Args:
        cr: Database cursor.
        diagnostics: PostgreSQL error diagnostics object with column_name,
                    constraint_name, and table_name attributes.
        check_registry: If True and column_name is not available, query
                       pg_constraint to find the columns.

    Returns:
        List of column names affected by the constraint, or empty list if
        columns cannot be determined.
    """
    if column := diagnostics.column_name:
        return [column]
    if not check_registry:
        return []
    cr.execute(
        SQL(
            """
        SELECT
            ARRAY(
                SELECT attname FROM pg_attribute
                WHERE attrelid = conrelid
                AND attnum = ANY(conkey)
            ) as "columns"
        FROM pg_constraint
        JOIN pg_class t ON t.oid = conrelid
        WHERE conname = %s
            AND t.relname = %s
            AND t.relnamespace = current_schema::regnamespace
    """,
            diagnostics.constraint_name,
            diagnostics.table_name,
        )
    )
    columns = cr.fetchone()
    return columns[0] if columns else []


# =============================================================================
# Company Domain Helpers
# =============================================================================


def check_company_domain_parent_of(self: BaseModel, companies):
    """A ``_check_company_domain`` function for single company_id fields.

    Lets a record be used if either:
    - record.company_id = False (shared between all companies), or
    - record.company_id is a parent of any of the given companies.

    Args:
        self: The model instance (provides access to env).
        companies: Company recordset, list of IDs, single ID, or field reference string.

    Returns:
        Domain list for filtering records.
    """
    if isinstance(companies, str):
        return [
            "|",
            ("company_id", "=", False),
            ("company_id", "parent_of", companies),
        ]

    companies = to_record_ids(companies)
    if not companies:
        return [("company_id", "=", False)]

    return [
        (
            "company_id",
            "in",
            [
                int(parent)
                for rec in self.env["res.company"].sudo().browse(companies)
                for parent in rec.parent_path.split("/")[:-1]
            ]
            + [False],
        )
    ]


def check_companies_domain_parent_of(self: BaseModel, companies):
    """A ``_check_company_domain`` function for multi-company company_ids fields.

    Lets a record be used if any company in record.company_ids is a parent
    of any of the given companies.

    Args:
        self: The model instance (provides access to env).
        companies: Company recordset, list of IDs, single ID, or field reference string.

    Returns:
        Domain list for filtering records.
    """
    if isinstance(companies, str):
        return [("company_ids", "parent_of", companies)]

    companies = to_record_ids(companies)
    if not companies:
        return []

    return [
        (
            "company_ids",
            "in",
            [
                int(parent)
                for rec in self.env["res.company"].sudo().browse(companies)
                for parent in rec.parent_path.split("/")[:-1]
            ],
        )
    ]
