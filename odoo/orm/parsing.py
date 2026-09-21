import functools
import re
import typing

_FIX_DB_ID_RE = re.compile(r"([^/])\.id(?=/|\Z)")
_FIX_EXTERNAL_ID_RE = re.compile(r"([^/]):id(?=/|\Z)")

regex_read_group_spec = re.compile(r"(\w+)(\.([\w\.]+))?(?::(\w+))?$")

regex_field_agg = re.compile(r"(\w+)(?::(\w+)(?:\((\w+)\))?)?")

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


_PARSE_CACHE_MAXSIZE = 2048


@functools.lru_cache(maxsize=_PARSE_CACHE_MAXSIZE)
def parse_field_expr(field_expr: str) -> tuple[str, str | None]:
    raw = field_expr
    if (property_index := field_expr.find(".")) >= 0:
        property_name = field_expr[property_index + 1 :]
        field_expr = field_expr[:property_index]
    else:
        property_name = None
    if not field_expr or (property_name is not None and not property_name):
        raise ValueError(f"Invalid field expression {raw!r}")
    if property_name is not None and (
        property_name.startswith(".")
        or property_name.endswith(".")
        or ".." in property_name
    ):
        raise ValueError(f"Invalid field expression {raw!r}")
    return field_expr, property_name


@functools.lru_cache(maxsize=_PARSE_CACHE_MAXSIZE)
def parse_read_group_spec(spec: str) -> tuple[str, str | None, str | None]:
    res_match = regex_read_group_spec.match(spec)
    if not res_match:
        raise ValueError(
            f"Invalid aggregate/groupby specification {spec!r}.\n"
            '- Valid aggregate specification looks like "<field_name>:<agg>" example: "quantity:sum".\n'
            '- Valid groupby specification looks like "<no_datish_field_name>" or "<datish_field_name>:<granularity>" example: "date:month" or "<properties_field_name>.<property>:<granularity>".'
        )

    groups = res_match.groups()
    return groups[0], groups[2], groups[3]


@functools.lru_cache(maxsize=_PARSE_CACHE_MAXSIZE)
def fix_import_export_id_paths(fieldname: str) -> tuple[str, ...]:
    fixed_db_id = _FIX_DB_ID_RE.sub(r"\1/.id", fieldname)
    fixed_external_id = _FIX_EXTERNAL_ID_RE.sub(r"\1/id", fixed_db_id)
    return tuple(fixed_external_id.split("/"))


class OrderTerm(typing.NamedTuple):
    """One comma-separated term of an ORDER BY string, already decided.

    `nulls_first` carries the default the three readers agreed on before this
    existed: absent a NULLS clause, a descending term puts them first.
    """

    field: str
    property: str | None
    func: str | None
    desc: bool
    nulls_first: bool


@functools.lru_cache(maxsize=_PARSE_CACHE_MAXSIZE)
def parse_order(order: str) -> tuple[OrderTerm, ...] | None:
    """Every term of `order`, or None if any of them does not parse.

    Cached on the string: an order is a property of a model or of a view, so
    the same handful of strings are parsed over and over.
    """
    terms = []
    for part in order.split(","):
        match = regex_order.match(part)
        if match is None:
            return None
        desc = (match["direction"] or "").upper() == "DESC"
        nulls = (match["nulls"] or "").upper()
        terms.append(
            OrderTerm(
                field=match["field"],
                property=match["property"],
                func=match["func"],
                desc=desc,
                nulls_first=(nulls == "NULLS FIRST") if nulls else desc,
            )
        )
    return tuple(terms)
