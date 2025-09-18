"""Standalone field-value cache for the ORM.

This module provides :class:`FieldCache`, an isolated data structure that
manages cached field values, dirty tracking, and deferred x2many patches.
It has **no dependency** on Environment, BaseModel, or database cursors,
making it fully testable with pure Python unit tests.

The cache is keyed by *field objects* (any hashable key) and record IDs.

Usage from Transaction::

    cache_store = FieldCache()
    cache_store.set_value(field, record_id, value)
    cache_store.mark_dirty(field, [record_id])
"""

import collections
from collections import defaultdict
from collections.abc import Collection, Iterable, Iterator

# Sentinel for missing values — distinct from any real cached value (including None).
_MISSING = object()


class FieldCache:
    """Standalone cache for field values, keyed by field objects and record IDs.

    Internal data structures:

    * ``_data``: ``{field: {record_id: value}}`` — cached values.
    * ``_dirty``: ``{field: set_of_ids}`` — ids whose cached value differs from DB.
    * ``_patches``: ``{field: {record_id: [ids_to_add]}}`` — deferred x2many additions.

    The ``_data`` and ``_dirty`` dicts use ``defaultdict`` so that first access
    auto-creates the sub-dict/set, matching the original Transaction behavior.
    ``_patches`` uses a nested defaultdict for the same reason.
    """

    __slots__ = ("_data", "_dirty", "_patches")

    def __init__(self, dirty_factory: type | None = None) -> None:
        self._data: defaultdict = defaultdict(dict)
        self._dirty: defaultdict = defaultdict(dirty_factory or set)
        self._patches: defaultdict = defaultdict(lambda: defaultdict(list))

    # ------------------------------------------------------------------
    # Data access
    # ------------------------------------------------------------------

    def get_field_data(self, field) -> dict:
        """Return the cache dict for *field*, creating it if needed.

        This is the low-level accessor that Field._get_cache_impl() uses.
        The returned dict is the *live* dict — mutations are visible to the cache.
        """
        return self._data[field]

    def get_field_data_or_none(self, field) -> dict | None:
        """Return the cache dict for *field*, or ``None`` if nothing is cached."""
        return self._data.get(field)

    def set_value(self, field, record_id, value) -> None:
        """Set a single cached value."""
        self._data[field][record_id] = value

    def get_value(self, field, record_id, default=_MISSING):
        """Return the cached value, or *default* if not present.

        Raises ``KeyError`` if *default* is not provided and the value is missing.
        """
        try:
            return self._data[field][record_id]
        except KeyError:
            if default is _MISSING:
                raise
            return default

    def has_value(self, field, record_id) -> bool:
        """Return whether *record_id* has a cached value for *field*."""
        field_cache = self._data.get(field)
        return field_cache is not None and record_id in field_cache

    def insert_if_absent(self, field, ids: Iterable, values: Iterable) -> None:
        """Set values only for IDs that are not already cached.

        Equivalent to ``dict.setdefault`` in bulk — preserves pending updates
        by not overwriting existing entries.  Uses ``collections.deque`` with
        ``maxlen=0`` to consume the ``map(setdefault, ...)`` iterator in C,
        which is ~15% faster than an explicit Python loop.
        """
        field_cache = self._data[field]
        collections.deque(map(field_cache.setdefault, ids, values, strict=False), maxlen=0)

    def update_batch(self, field, ids: tuple, value) -> None:
        """Set the same *value* for all *ids*.

        Optimized for the common singleton case (``len(ids) == 1``).
        """
        field_cache = self._data[field]
        if len(ids) <= 1:
            if ids:
                field_cache[ids[0]] = value
        else:
            field_cache.update(dict.fromkeys(ids, value))

    def pop_value(self, field, record_id, default=_MISSING):
        """Remove and return a cached value."""
        field_cache = self._data.get(field)
        if field_cache is None:
            if default is _MISSING:
                raise KeyError((field, record_id))
            return default
        if default is _MISSING:
            return field_cache.pop(record_id)
        return field_cache.pop(record_id, default)

    # ------------------------------------------------------------------
    # Dirty tracking
    # ------------------------------------------------------------------

    def mark_dirty(self, field, ids: Iterable) -> None:
        """Mark *ids* as dirty for *field*."""
        self._dirty[field].update(ids)

    def get_dirty(self, field) -> set | None:
        """Return the set of dirty IDs for *field*, or ``None``."""
        return self._dirty.get(field)

    def pop_dirty(self, field) -> set | None:
        """Remove and return the set of dirty IDs for *field*."""
        return self._dirty.pop(field, None)

    def pop_dirty_for_model(self, model_name: str) -> dict:
        """Pop all dirty fields belonging to *model_name*.

        More efficient than iterating all model fields and popping each:
        iterates the (usually small) dirty dict instead.  O(n_dirty_global)
        vs O(n_model_fields).
        """
        result = {}
        for field in list(self._dirty):
            if field.model_name == model_name:
                ids = self._dirty.pop(field)
                if ids:
                    result[field] = ids
        return result

    def is_any_dirty(self) -> bool:
        """Return whether any field has dirty entries."""
        return bool(self._dirty)

    def has_dirty_field(self, field) -> bool:
        """Return whether *field* has any dirty entries."""
        return bool(self._dirty.get(field))

    def iter_dirty_fields(self) -> Iterator:
        """Iterate over fields that have dirty entries."""
        return iter(self._dirty)

    def dirty_entry_count(self) -> int:
        """Return the total number of dirty (field, record_id) entries."""
        return sum(len(ids) for ids in self._dirty.values())

    # ------------------------------------------------------------------
    # Patches (deferred x2many additions)
    # ------------------------------------------------------------------

    def add_patch(self, field, record_id, new_id) -> None:
        """Record a deferred x2many addition."""
        self._patches[field][record_id].append(new_id)

    def get_patches(self, field) -> dict | None:
        """Return the patches dict for *field*, or ``None``."""
        return self._patches.get(field)

    # ------------------------------------------------------------------
    # Invalidation
    # ------------------------------------------------------------------

    def invalidate_field(self, field, ids: Collection | None = None) -> None:
        """Invalidate cached values for *field*.

        If *ids* is ``None``, clear the entire field cache.
        Otherwise, remove only the specified record IDs.
        """
        field_cache = self._data.get(field)
        if field_cache is None:
            return
        if ids is None:
            field_cache.clear()
        else:
            for id_ in ids:
                field_cache.pop(id_, None)

    def invalidate_all(self) -> None:
        """Clear all cached data except dirty entries.

        Dirty entries are preserved in ``_data`` so that a subsequent
        :meth:`flush <odoo.orm.models.mixins.cache.CacheMixin._flush>`
        can still read their values via :meth:`~odoo.orm.fields.base.Field.get_column_update`.
        Non-dirty cached data is cleared to force re-fetching from the
        database on next access.

        ``_dirty`` flags and ``_patches`` are never touched.
        """
        if not self._dirty:
            self._data.clear()
            return
        # Keep field_cache dicts that contain dirty entries.  We preserve
        # the *entire* sub-dict for a dirty field (not just the dirty IDs)
        # because context-dependent fields (translate=True, company_dependent)
        # store values across multiple cache-key sub-dicts, and the flush
        # reads from all of them.
        for field in list(self._data):
            if field not in self._dirty:
                del self._data[field]

    def clear(self) -> None:
        """Clear everything: data, dirty flags, and patches."""
        self._data.clear()
        self._dirty.clear()
        self._patches.clear()

    # ------------------------------------------------------------------
    # Iteration & introspection
    # ------------------------------------------------------------------

    def iter_fields(self) -> Iterator:
        """Iterate over fields that have cached data."""
        return iter(self._data)

    def iter_field_items(self) -> Iterator:
        """Iterate over (field, field_cache_dict) pairs."""
        return iter(self._data.items())

    def has_field(self, field) -> bool:
        """Return whether *field* has any cached data."""
        return field in self._data

    def __repr__(self) -> str:
        n_fields = len(self._data)
        n_dirty = sum(len(ids) for ids in self._dirty.values())
        return f"<FieldCache fields={n_fields} dirty_entries={n_dirty}>"
