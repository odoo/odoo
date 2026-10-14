# Part of Odoo. See LICENSE file for full copyright and licensing details.

from typing import Self

from odoo.tools import frozendict

from .models import api, Model


class CachedModel(Model):
    """ The abstract model 'ir.cached.data' is used as a mixin to provide a stable
    cache for some fields of the model's records.  It uses the cache named
    ``'stable'`` and automatically invalidates it based on ``_clear_cache_name``.

    Translated fields may be cached: their value is kept for all the languages
    (as stored in database), so that a single cache entry serves every language
    and the cache key never depends on ``env.lang``.
    """
    _register: bool = False  # not visible in ORM registry, meant to be Python-inherited only

    _clear_cache_name = 'stable'

    _cached_data_domain = []
    """domain of the records to cache"""

    _cached_data_fields: tuple[str, ...] = ()
    """the fields to cache for the records to cache. Please promise all these
    fields don't depend on other models and context."""

    @property
    def _clear_cache_on_fields(self):
        return self._cached_data_fields

    def _use_cached_data(self) -> bool:
        """ Return whether the cached data may be used.

        It may not be while the database schema is being set up: a module may
        add a field to a cached model, and that field is in the registry before
        its column is created in database.  Reading all the cached fields at
        once would then fail on the column that does not exist yet.  This is
        exactly what ``prefetch_fields`` tells, as ``_auto_init`` turns it off
        for that reason.
        """
        return self.env.context.get('prefetch_fields', True) and bool(self._cached_data_fields)

    @api.model
    @api.private
    def _get_cacheable_field_names(self) -> tuple[str, ...]:
        """ Return the names of the fields that can safely be put in the cache:
        stored columns, prefetched with the record, not restricted to some
        groups, and whose value depends neither on the context nor on the
        current company.

        This is meant to be used to build ``_cached_data_fields``, so that a
        field added by another module does not silently cost a query again.
        """
        field_depends_context = self.env._field_depends_context
        return tuple(
            name
            for name, field in self._fields.items()
            if name != 'id'
            if field.store and field.column_type
            if field.prefetch is True
            if not field.groups
            if not field.company_dependent
            if field not in field_depends_context
        )

    @api.ormcache(cache='stable')
    def _cached_data(self) -> frozendict:
        """ Return the cached values for all records that satisfy ``_cached_data_domain``.
        The result is a mapping where keys are field names (including field ``id``)
        and values are tuples of cached values.
        """
        fnames = self._cached_data_fields
        assert fnames, "missing fields to cache"
        # the values are kept across transactions: the pending computations must
        # be done first, otherwise a stored computed field would be cached with
        # the value it had before its dependencies changed.  Only the
        # computations are processed: flushing to database here would run the
        # model constraints in the middle of an unrelated write.
        self._recompute_model(fnames)
        # 'prefetch_langs' keeps the value of translated fields for all the
        # languages, so that the cached data does not depend on 'env.lang'
        records = self.sudo().with_context({'active_test': False, 'prefetch_langs': True}).search_fetch(
            self._cached_data_domain, fnames, order='id')

        # each field is mapped to a tuple
        result = {'id': records._ids}
        for fname in fnames:
            field_cache = self._fields[fname]._get_cache(records.env)
            result[fname] = tuple(map(field_cache.__getitem__, records.ids))
        return frozendict(result)

    def _fetch_field(self, field):
        if any(self._ids) and self._use_cached_data() and field.name in self._cached_data_fields:
            self.check_field_access(field, 'read')
            data = self._cached_data()
            records = self.browse(data['id'])
            if field.translate:
                records = records.with_context(prefetch_langs=True)
            field._insert_cache(records, data[field.name])
            data_ids = set(data['id'])
            if all(record_id in data_ids for record_id in self._ids):
                self.check_access('read')
                return
        super()._fetch_field(field)

    @api.model
    @api.private
    def get_all(self) -> Self:
        """Get all instances in cache.

        Warning: the result is filtered neither by the record rules nor by
        ``active_test``; only use it on models whose records are all visible to
        everyone, and filter explicitly otherwise.
        """
        return self.browse(self._cached_data()['id'])
