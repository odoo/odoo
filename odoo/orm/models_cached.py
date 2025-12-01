# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools import frozendict, ormcache

from .models import Model


class CachedModel(Model):
    """ The abstract model 'ir.cached.data' is used as a mixin to provide a stable
    cache for some fields of the model's records.  It uses the cache named
    ``'stable'`` and automatically invalidates it based on ``_clear_cache_name``.
    """
    _register: bool = False  # not visible in ORM registry, meant to be Python-inherited only

    _clear_cache_name = 'stable'

    _cached_data_domain = []
    """domain of the records to cache"""

    _cached_data_fields: tuple[str] = ()
    """the fields to cache for the records to cache. Please promise all these
    fields don't depend on other models and context and are not translated."""

    @property
    def _clear_cache_on_fields(self):
        return self._cached_data_fields

    @ormcache(cache='stable')
    def _cached_data(self) -> frozendict:
        """ Return the cached values for all records that satisfy ``_cached_data_domain``.
        The result is a mapping where keys are field names (including field ``id``)
        and values are tuples of cached values.
        """
        fnames = self._cached_data_fields
        assert fnames, "missing fields to cache"
        records = self.sudo().with_context({'active_test': False}).search_fetch(
            self._cached_data_domain, fnames, order='id')

        # each field is mapped to a tuple
        result = {'id': records._ids}
        for fname in fnames:
            field = self._fields[fname]
            if field.compute and not field.store:
                records.mapped(fname)  # fill the cache for computed field
            result[fname] = tuple(map(field._get_cache(records.env).__getitem__, records.ids))
        return frozendict(result)

    def _fetch_field(self, field):
        if any(self._ids) and field.name in self._cached_data_fields:
            self._check_field_access(field, 'read')
            data = self._cached_data()
            field._insert_cache(self.browse(data['id']), data[field.name])
            data_ids = set(data['id'])
            if all(record_id in data_ids for record_id in self._ids):
                self.check_access('read')
                return
        super()._fetch_field(field)
