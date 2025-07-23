# Part of Odoo. See LICENSE file for full copyright and licensing details.

from typing import Self

from odoo.tools import frozendict, sql

from .models import api, Model


class CachedModel(Model):
    """ Provides a stable cache for some fields of the model's records.  It uses
    the cache named ``'stable'`` and automatically invalidates it based on
    ``_clear_cache_name``.
    """
    _register: bool = False  # not visible in ORM registry, meant to be Python-inherited only

    _clear_cache_name = 'stable'

    _cached_data_domain = []
    """domain of the records to cache"""

    _cached_data_fields: tuple[str] = ()
    """the fields to cache for the records to cache. Please promise all these
    fields don't depend on other models and context."""

    @property
    def _clear_cache_on_fields(self):
        return self._cached_data_fields

    @api.ormcache(cache='stable')
    def _cached_data(self) -> frozendict:
        """ Return the cached values for all records that satisfy ``_cached_data_domain``.
        The result is a mapping where keys are field names (including field ``id``)
        and values are tuples of cached values.
        """
        fnames = self._cached_data_fields
        assert fnames, "missing fields to cache"
        self.invalidate_model([fname for fname in fnames if self._fields[fname].translate])
        records = self.sudo().with_context({'active_test': False, 'prefetch_langs': True}).search_fetch(
            self._cached_data_domain, fnames)

        # each field is mapped to a tuple
        result = {'id': records._ids}
        for fname in fnames:
            field_cache = self._fields[fname]._get_cache(records.env)
            result[fname] = tuple(map(field_cache.__getitem__, records.ids))
        return frozendict(result)

    def _fetch_field(self, field):
        if any(self._ids) and field.name in self._cached_data_fields:
            self.check_field_access(field, 'read')
            data = self._cached_data()
            field._insert_cache(self.with_context(prefetch_langs=True).browse(data['id']), data[field.name])
            data_ids = set(data['id'])
            if all(record_id in data_ids for record_id in self._ids):
                self.check_access('read')
                return
        super()._fetch_field(field)

    @api.model
    @api.private
    def get_all(self) -> Self:
        """Get all instances in cache."""
        return self.browse(self._cached_data()['id'])

    @api.model
    def read_all(self):
        records = self.get_all()
        fnames = self._cached_data_fields
        return records._read_format(fnames=fnames)


class ValueModel(CachedModel):
    """ Defines a model for which we have access to records by a code field
    (``_code_field = 'code'``). That field is unique for the model and some
    of the values are cached.
    """
    _register: bool = False     # not visible in ORM registry, meant to be python-inherited only

    _code_field: str = 'code'
    """the unique identifier field on the model.
    It is uniquely indexed by the ORM and must be stored.
    """

    @api.private
    @api.model
    def get(self, key):
        return self.browse(self._get_id_by_code().get(key, ()))

    @api.model
    @api.ormcache(cache='stable')
    def _get_id_by_code(self):
        data = self._cached_data()
        return frozendict(zip(data[self._code_field], data['id']))

    def _auto_init(self):
        super()._auto_init()

        code_field = self._fields[self._code_field]
        assert code_field.column_type[0] == 'varchar', \
            f"The code field must be a char: {code_field}, got {code_field.column_type[0]}"
        assert code_field.store and code_field.required and not code_field.translate, \
            f"The code field must be required stored untranslated char: {code_field}"
        assert not code_field.index, f"The index is managed automatically on {code_field}"

        indexname = sql.make_index_name(self._table, code_field.name + '_u')
        sql.create_index(self.env.cr, indexname, self._table, [code_field.name], 'btree', unique=True)
