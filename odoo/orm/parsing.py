"""
Expression and specification parsing for the ORM.

Provides parsing functions used across the ORM for field expressions,
read_group specifications, and import/export field paths. Absorbs the
regex patterns that were previously in core/constants.py.

This is the most widely shared utility in the ORM (6+ consumers for
parse_field_expr alone).
"""

import functools
import re

# =============================================================================
# Parsing Patterns
# =============================================================================

# For import/export field path ID fixing
_FIX_DB_ID_RE = re.compile(r"([^/])\.id")
_FIX_EXTERNAL_ID_RE = re.compile(r"([^/]):id")

# For _read_group (new API)
regex_read_group_spec = re.compile(r"(\w+)(\.([\w\.]+))?(?::(\w+))?$")

# For read_group (old API)
regex_field_agg = re.compile(r"(\w+)(?::(\w+)(?:\((\w+)\))?)?")

# For ORDER BY in read_group context (single order part, no anchors)
regex_order_part_read_group = re.compile(
    r"""
    \s*
    (?P<term>(?P<field>[a-z0-9_]+)(\.([\w\.]+))?(:(?P<func>[a-z_]+))?)
    (\s+(?P<direction>desc|asc))?
    (\s+(?P<nulls>nulls\ first|nulls\ last))?
    \s*
""",
    re.IGNORECASE | re.VERBOSE,
)

# For ORDER BY clause parsing (used by search and sort operations)
regex_order = re.compile(
    r"""
    ^
    (\s*
        (?P<term>((?P<field>[a-z0-9_]+)(\.(?P<property>[a-z0-9_]+))?(:(?P<func>[a-z_]+))?))
        (\s+(?P<direction>desc|asc))?
        (\s+(?P<nulls>nulls\ first|nulls\ last))?
        \s*
        (,|$)
    )+
    (?<!,)
    $
""",
    re.IGNORECASE | re.VERBOSE,
)


# =============================================================================
# Parsing Functions
# =============================================================================


@functools.cache
def parse_field_expr(field_expr: str) -> tuple[str, str | None]:
    """Parse a field expression into field name and optional property name.

    Args:
        field_expr: A field expression like "field_name" or "field_name.property".

    Returns:
        A tuple of (field_name, property_name) where property_name may be None.

    Raises:
        ValueError: If the field expression is empty or invalid.

    Examples:
        >>> parse_field_expr("amount")
        ('amount', None)
        >>> parse_field_expr("partner_id.name")
        ('partner_id', 'name')
    """
    if (property_index := field_expr.find(".")) >= 0:
        property_name = field_expr[property_index + 1 :]
        field_expr = field_expr[:property_index]
    else:
        property_name = None
    if not field_expr:
        raise ValueError(f"Invalid field expression {field_expr!r}")
    return field_expr, property_name


@functools.cache
def parse_read_group_spec(spec: str) -> tuple[str, str | None, str | None]:
    """Return a triplet corresponding to the given field/property_name/aggregate specification.

    Args:
        spec: A read_group specification like "amount:sum" or "date:month".

    Returns:
        A tuple of (field_name, property_name, aggregate/granularity).

    Raises:
        ValueError: If the specification format is invalid.

    Examples:
        >>> parse_read_group_spec("amount:sum")
        ('amount', None, 'sum')
        >>> parse_read_group_spec("date:month")
        ('date', None, 'month')
        >>> parse_read_group_spec("properties.color:count")
        ('properties', 'color', 'count')
    """
    res_match = regex_read_group_spec.match(spec)
    if not res_match:
        raise ValueError(
            f"Invalid aggregate/groupby specification {spec!r}.\n"
            '- Valid aggregate specification looks like "<field_name>:<agg>" example: "quantity:sum".\n'
            '- Valid groupby specification looks like "<no_datish_field_name>" or "<datish_field_name>:<granularity>" example: "date:month" or "<properties_field_name>.<property>:<granularity>".'
        )

    groups = res_match.groups()
    return groups[0], groups[2], groups[3]


@functools.cache
def fix_import_export_id_paths(fieldname: str) -> tuple[str, ...]:
    """Fix the id fields in import and exports, and split field paths on '/'.

    This function handles special id field syntax used in import/export operations:
    - Converts ".id" (database id) to "/.id"
    - Converts ":id" (external id) to "/id"

    Args:
        fieldname: Name of the field path to import/export.

    Returns:
        Split field path as a tuple of strings.

    Examples:
        >>> fix_import_export_id_paths("partner_id.id")
        ('partner_id', '.id')
        >>> fix_import_export_id_paths("partner_id:id")
        ('partner_id', 'id')
        >>> fix_import_export_id_paths("partner_id/name")
        ('partner_id', 'name')
    """
    fixed_db_id = _FIX_DB_ID_RE.sub(r"\1/.id", fieldname)
    fixed_external_id = _FIX_EXTERNAL_ID_RE.sub(r"\1/id", fixed_db_id)
    return tuple(fixed_external_id.split("/"))
