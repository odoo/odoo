"""Pure Python fallback for field cache access functions.

Used when the Rust extension (odoo_rust) is not installed.
These implementations are semantically identical to the Rust versions
but slower due to Python loop and function call overhead.
"""


def batch_cache_get(
    field_cache: dict,
    ids: tuple,
    pending: object,
    none_val: object,
) -> tuple[list, list[int]]:
    """Batch cache lookup for mapped()/grouped() identity-type fast paths.

    Returns (results, miss_indices) where:
    - results[i] = cached value (or none_val if cache value is None)
    - miss_indices = positions where cache was empty or value was PENDING
    """
    results = []
    miss_indices = []
    _get = field_cache.get
    _MISSING = object()
    _append_result = results.append
    _append_miss = miss_indices.append

    for i, id_ in enumerate(ids):
        value = _get(id_, _MISSING)
        if value is _MISSING or value is pending:
            _append_result(none_val)
            _append_miss(i)
        elif value is None:
            _append_result(none_val)
        else:
            _append_result(value)

    return results, miss_indices


def batch_cache_filter(
    field_cache: dict,
    ids: tuple,
    pending: object,
) -> tuple[list, list[int]]:
    """Batch cache truthiness filter for filtered() field-name fast path.

    Returns (passing_ids, miss_indices) where:
    - passing_ids = list of record IDs where cached value is truthy
    - miss_indices = positions where cache miss or PENDING
    """
    passing_ids = []
    miss_indices = []
    _get = field_cache.get
    _MISSING = object()
    _append_pass = passing_ids.append
    _append_miss = miss_indices.append

    for i, id_ in enumerate(ids):
        value = _get(id_, _MISSING)
        if value is _MISSING or value is pending:
            _append_miss(i)
        elif value:
            _append_pass(id_)
        # falsy: neither pass nor miss

    return passing_ids, miss_indices


def batch_cache_values(
    field_cache: dict,
    ids: tuple,
    pending: object,
) -> list | None:
    """All-or-nothing batch cache extraction for sorted() fast path.

    Returns a list of all cached values, or None if any id is missing
    or has a PENDING value.  Early bailout on first miss.
    """
    values = []
    _get = field_cache.get
    _MISSING = object()
    _append = values.append

    for id_ in ids:
        value = _get(id_, _MISSING)
        if value is _MISSING or value is pending:
            return None
        _append(value)

    return values


def scalar_cache_get(
    env_dict: dict,
    field: object,
    record_id: object,
    pending: object,
    sentinel: object,
) -> object:
    """Single-record cache lookup for _make_scalar_get hot path.

    Performs: env_dict["_field_cache_memo"][field][record_id]
    Returns the cached value, or sentinel on any miss or PENDING.
    """
    try:
        value = env_dict["_field_cache_memo"][field][record_id]
    except KeyError:
        return sentinel
    if value is pending:
        return sentinel
    return value
