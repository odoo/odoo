import json
from collections import abc

from odoo.tools.misc import frozendict
from odoo import _


class GoogleApiResource(abc.Set):
    """Abstract base class for Google API resource sets (events, calendars, etc.).

    Inspired by Odoo recordset, one instance can be a single resource or an
    (immutable) set of resources. All usual set operations are supported.

    Subclasses must implement `_get_model`.
    Optionally, it may also implement `_load_odoo_ids_from_metadata`
    """

    def __init__(self, iterable=()):
        items = {}
        for item in iterable:
            if isinstance(item, self.__class__):
                items[item.id] = item._items[item.id]
            elif isinstance(item, abc.Mapping):
                items[item.get('id')] = item
            else:
                raise TypeError(
                    _("Only %s or iterable of dict are supported", self.__class__.__name__)
                )
        self._items = frozendict(items)

    def __iter__(self) -> abc.Iterator['GoogleApiResource']:
        return iter(self.__class__([vals]) for vals in self._items.values())

    def __add__(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError("Both instances must be of type %s." % self.__class__.__name__)
        # Fast path for empty sets, as event sets are immutable.
        if not self:
            return other
        if not other:
            return self
        # Merge the underlying dictionaries directly.
        return self.__class__({**self._items, **other._items})

    def __contains__(self, item):
        return item.id in self._items

    def __len__(self):
        return len(self._items)

    def __bool__(self):
        return bool(self._items)

    def __getattr__(self, name):
        # ensure_one
        try:
            item_id, = self._items.keys()
        except ValueError:
            raise ValueError("Expected singleton: %s" % self)
        value = self._items[item_id].get(name)
        json.dumps(value)
        return value

    def __repr__(self):
        return '%s%s' % (self.__class__.__name__, self.ids)

    @property
    def ids(self):
        return tuple(item.id for item in self)

    def filter(self, func) -> 'GoogleApiResource':
        return self.__class__(item for item in self if func(item))

    def odoo_id(self, env):
        self.odoo_ids(env)  # load ids
        return self._odoo_id

    def _meta_odoo_id(self, dbname):
        """Returns the Odoo id stored in the Google Event metadata.
        This id might not actually exists in the database.
        """
        properties = self.extendedProperties and (self.extendedProperties.get('shared', {}) or self.extendedProperties.get('private', {})) or {}
        o_id = properties.get('%s_odoo_id' % dbname)
        if o_id:
            return int(o_id)

    def odoo_ids(self, env):
        ids = tuple(item._odoo_id for item in self if item._odoo_id)
        if len(ids) == len(self):
            return ids
        model = self._get_model(env)
        found = self._load_odoo_ids_from_db(env, model)
        unsure = self - found
        if unsure:
            unsure._load_odoo_ids_from_metadata(env, model)
        # skip unmatched ids because we browse the result
        return tuple(item._odoo_id for item in self if item._odoo_id)

    def _get_model(self, env):
        raise NotImplementedError("Subclasses must implement _get_model")

    def _load_odoo_ids_from_db(self, env, model):
        odoo_items = model.with_context(active_test=False)._from_google_ids(self.ids)
        mapping = {item.google_id: item.id for item in odoo_items}  # {google_id: odoo_id}
        existing_google_ids = odoo_items.mapped('google_id')
        for item in self:
            odoo_id = mapping.get(item.id)
            if odoo_id:
                item._items[item.id]['_odoo_id'] = odoo_id
        return self.filter(lambda item: item.id in existing_google_ids)

    def _load_odoo_ids_from_metadata(self, env, model):
        return
