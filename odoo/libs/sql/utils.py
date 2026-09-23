__all__ = [
    "escape_psql",
    "get_index_name",
    "normalize_identifier",
    "pg_varchar",
    "reverse_order",
]

import itertools
from binascii import crc32


def escape_psql(to_escape: str) -> str:
    return to_escape.replace("\\", r"\\").replace("%", r"\%").replace("_", r"\_")


def pg_varchar(size: int | None = 0) -> str:
    if size is None:
        return "VARCHAR"
    if not isinstance(size, int) or isinstance(size, bool):
        raise ValueError(f"VARCHAR parameter should be an int, got {type(size)}")
    if size < 0:
        raise ValueError(f"VARCHAR parameter should not be negative, got {size}")
    return f"VARCHAR({size})" if size else "VARCHAR"


def _split_order_items(order: str) -> list[str]:
    items: list[str] = []
    depth = 0
    in_quote = False
    start = 0
    for i, ch in enumerate(order):
        if ch == '"':
            in_quote = not in_quote
        elif in_quote:
            continue
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            items.append(order[start:i])
            start = i + 1
    items.append(order[start:])
    return items


def reverse_order(order: str) -> str:
    items = []
    for item in _split_order_items(order):
        tokens = item.split()
        if not tokens:
            continue

        nulls = ""
        if len(tokens) >= 3 and tokens[-2].lower() == "nulls":
            nulls = " nulls first" if tokens[-1].lower() == "last" else " nulls last"
            tokens = tokens[:-2]

        direction = "asc" if tokens[-1].lower() == "desc" else "desc"
        if tokens[-1].lower() in ("asc", "desc"):
            tokens = tokens[:-1]
        if not tokens:
            continue
        items.append(f"{' '.join(tokens)} {direction}{nulls}")
    return ", ".join(items)


def normalize_identifier(identifier: str) -> str:
    encoded = identifier.encode()
    if len(encoded) > 63:
        prefix = encoded[:54].decode(errors="ignore")
        return f"{prefix}_{crc32(encoded):08x}"
    return identifier


def get_index_name(table_name: str, column_name: str) -> str:
    return normalize_identifier(f"{table_name}__{column_name}_index")


_SIZE_PRETTY_UNITS = (
    ("bytes", 10 * 1024, False, 0),
    ("kB", 20 * 1024 - 1, True, 10),
    ("MB", 20 * 1024 - 1, True, 20),
    ("GB", 20 * 1024 - 1, True, 30),
    ("TB", 20 * 1024 - 1, True, 40),
    ("PB", 20 * 1024 - 1, True, 50),
)


def _truncating_div(size: int, divisor: int) -> int:
    return -(-size // divisor) if size < 0 else size // divisor


def pg_size_pretty(size: int) -> str:
    # PostgreSQL's pg_size_pretty(bigint), unit table and all: a rounding
    # unit keeps one bit past its own to half-round with, and C division
    # truncates toward zero, which a negative size shows
    for current, following in itertools.pairwise(_SIZE_PRETTY_UNITS):
        unit, limit, rounds, bits = current
        if abs(size) < limit:
            break
        _unit, _limit, next_rounds, next_bits = following
        size = _truncating_div(size, 1 << (next_bits - bits - next_rounds + rounds))
    else:
        unit, _limit, rounds, _bits = _SIZE_PRETTY_UNITS[-1]
    if rounds:
        size = _truncating_div(size + (-1 if size < 0 else 1), 2)
    return f"{size} {unit}"
