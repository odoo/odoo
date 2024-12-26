from __future__ import annotations

import itertools
import logging
import typing
from collections import defaultdict
from operator import attrgetter

from odoo.exceptions import MissingError, UserError
from odoo.tools import SQL, OrderedSet, Query, sql, unique
from odoo.tools.constants import PREFETCH_MAX
from odoo.tools.misc import SENTINEL, Sentinel, unquote

from .commands import Command
from .domains import Domain
from .fields import IR_MODELS, Field, _logger
from .fields_reference import Many2oneReference
from .identifiers import NewId
from .models import BaseModel
from .utils import COLLECTION_TYPES, SQL_OPERATORS, check_pg_name

M = typing.TypeVar('M', bound=BaseModel)
if typing.TYPE_CHECKING:
    from .types import ContextType, DomainType

_schema = logging.getLogger('odoo.schema')


class _Relational(Field[M], typing.Generic[M]):
    """ Abstract class for relational fields. """
    relational = True
    domain: DomainType = []         # domain for searching values
    context: ContextType = {}       # context for searching values
    auto_join = False               # whether joins are generated upon search
    check_company = False

    def __get__(self, records, owner=None):
        # base case: do the regular access
        if records is None or len(records._ids) <= 1:
            return super().__get__(records, owner)

        # multi-record case
        if self.compute and self.store:
            self.recompute(records)

        # retrieve values in cache, and fetch missing ones
        env = records.env
        vals = env.cache.get_until_miss(records, self)

        if self.store and len(vals) < len(records) - PREFETCH_MAX:
            # a lot of missing records, just fetch that field
            remaining = records[len(vals):]
            remaining.fetch([self.name])
            vals += records.env.cache.get_until_miss(remaining, self)

        while len(vals) < len(records):
            remaining = records.__class__(records.env, records._ids[len(vals):], records._prefetch_ids)
            self.__get__(next(iter(remaining)))
            vals += records.env.cache.get_until_miss(remaining, self)

        assert len(vals) == len(records), "Some records are not in cache"
        return self.convert_to_record_multi(vals, records)

    def convert_to_record_multi(self, values, records):
        """ Convert a list of (relational field) values from the cache format to
        the record format, for the sake of optimization.
        """
        raise NotImplementedError

    def setup_nonrelated(self, model):
        super().setup_nonrelated(model)
        assert self.comodel_name in model.pool, \
            f"Field {self} with unknown comodel_name {self.comodel_name or '???'!r}"

    def get_domain_list(self, model):
        """ Return a list domain from the domain parameter. """
        # TODO rename and make it return a Domain
        domain = self.domain
        if callable(domain):
            domain = domain(model)
        return domain if isinstance(domain, list) else []

    @property
    def _related_domain(self):
        def validated(domain):
            if isinstance(domain, str) and not self.inherited:
                # string domains are expressions that are not valid for self's model
                return None
            return domain

        if callable(self.domain):
            # will be called with another model than self's
            return lambda recs: validated(self.domain(recs.env[self.model_name]))  # pylint: disable=not-callable
        else:
            return validated(self.domain)

    _related_context = property(attrgetter('context'))

    _description_relation = property(attrgetter('comodel_name'))
    _description_context = property(attrgetter('context'))

    def _description_domain(self, env):
        domain = self.domain(env[self.model_name]) if callable(self.domain) else self.domain  # pylint: disable=not-callable
        if self.check_company:
            field_to_check = None
            if self.company_dependent:
                cids = '[allowed_company_ids[0]]'
            elif self.model_name == 'res.company':
                # when using check_company=True on a field on 'res.company', the
                # company_id comes from the id of the current record
                cids = '[id]'
            elif 'company_id' in env[self.model_name]:
                cids = '[company_id]'
                field_to_check = 'company_id'
            elif 'company_ids' in env[self.model_name]:
                cids = 'company_ids'
                field_to_check = 'company_ids'
            else:
                _logger.warning(env._(
                    "Couldn't generate a company-dependent domain for field %s. "
                    "The model doesn't have a 'company_id' or 'company_ids' field, and isn't company-dependent either.",
                    f'{self.model_name}.{self.name}'
                ))
                return domain
            company_domain = env[self.comodel_name]._check_company_domain(companies=unquote(cids))
            if not field_to_check:
                return f"{company_domain} + {domain or []}"
            else:
                no_company_domain = env[self.comodel_name]._check_company_domain(companies='')
                return f"({field_to_check} and {company_domain} or {no_company_domain}) + ({domain or []})"
        return domain


class Many2one(_Relational[M]):
    """ The value of such a field is a recordset of size 0 (no
    record) or 1 (a single record).

    :param str comodel_name: name of the target model
        ``Mandatory`` except for related or extended fields.

    :param domain: an optional domain to set on candidate values on the
        client side (domain or a python expression that will be evaluated
        to provide domain)

    :param dict context: an optional context to use on the client side when
        handling that field

    :param str ondelete: what to do when the referred record is deleted;
        possible values are: ``'set null'``, ``'restrict'``, ``'cascade'``

    :param bool auto_join: whether JOINs are generated upon search through that
        field (default: ``False``)

    :param bool delegate: set it to ``True`` to make fields of the target model
        accessible from the current model (corresponds to ``_inherits``)

    :param bool check_company: Mark the field to be verified in
        :meth:`~odoo.models.Model._check_company`. Has a different behaviour
        depending on whether the field is company_dependent or not.
        Constrains non-company-dependent fields to target records whose
        company_id(s) are compatible with the record's company_id(s).
        Constrains company_dependent fields to target records whose
        company_id(s) are compatible with the currently active company.
    """
    type = 'many2one'
    _column_type = ('int4', 'int4')

    ondelete = None                     # what to do when value is deleted
    delegate = False                    # whether self implements delegation

    def __init__(self, comodel_name: str | Sentinel = SENTINEL, string: str | Sentinel = SENTINEL, **kwargs):
        super(Many2one, self).__init__(comodel_name=comodel_name, string=string, **kwargs)

    def _setup_attrs(self, model_class, name):
        super()._setup_attrs(model_class, name)
        # determine self.delegate
        if not self.delegate and name in model_class._inherits.values():
            self.delegate = True
        # self.delegate implies self.auto_join
        if self.delegate:
            self.auto_join = True

    def setup_nonrelated(self, model):
        super().setup_nonrelated(model)
        # 3 cases:
        # 1) The ondelete attribute is not defined, we assign it a sensible default
        # 2) The ondelete attribute is defined and its definition makes sense
        # 3) The ondelete attribute is explicitly defined as 'set null' for a required m2o,
        #    this is considered a programming error.
        if not self.ondelete:
            comodel = model.env[self.comodel_name]
            if model.is_transient() and not comodel.is_transient():
                # Many2one relations from TransientModel Model are annoying because
                # they can block deletion due to foreign keys. So unless stated
                # otherwise, we default them to ondelete='cascade'.
                self.ondelete = 'cascade' if self.required else 'set null'
            else:
                self.ondelete = 'restrict' if self.required else 'set null'
        if self.ondelete == 'set null' and self.required:
            raise ValueError(
                "The m2o field %s of model %s is required but declares its ondelete policy "
                "as being 'set null'. Only 'restrict' and 'cascade' make sense."
                % (self.name, model._name)
            )
        if self.ondelete == 'restrict' and self.comodel_name in IR_MODELS:
            raise ValueError(
                f"Field {self.name} of model {model._name} is defined as ondelete='restrict' "
                f"while having {self.comodel_name} as comodel, the 'restrict' mode is not "
                f"supported for this type of field as comodel."
            )

    def update_db(self, model, columns):
        comodel = model.env[self.comodel_name]
        if not model.is_transient() and comodel.is_transient():
            raise ValueError('Many2one %s from Model to TransientModel is forbidden' % self)
        return super(Many2one, self).update_db(model, columns)

    def update_db_column(self, model, column):
        super(Many2one, self).update_db_column(model, column)
        model.pool.post_init(self.update_db_foreign_key, model, column)

    def update_db_foreign_key(self, model, column):
        if self.company_dependent:
            return
        comodel = model.env[self.comodel_name]
        # foreign keys do not work on views, and users can define custom models on sql views.
        if not model._is_an_ordinary_table() or not comodel._is_an_ordinary_table():
            return
        # ir_actions is inherited, so foreign key doesn't work on it
        if not comodel._auto or comodel._table == 'ir_actions':
            return
        # create/update the foreign key, and reflect it in 'ir.model.constraint'
        model.pool.add_foreign_key(
            model._table, self.name, comodel._table, 'id', self.ondelete or 'set null',
            model, self._module
        )

    def _update(self, records, value):
        """ Update the cached value of ``self`` for ``records`` with ``value``. """
        cache = records.env.cache
        for record in records:
            cache.set(record, self, self.convert_to_cache(value, record, validate=False))

    def convert_to_column(self, value, record, values=None, validate=True):
        return value or None

    def convert_to_cache(self, value, record, validate=True):
        # cache format: id or None
        if type(value) is int or type(value) is NewId:
            id_ = value
        elif isinstance(value, BaseModel):
            if validate and (value._name != self.comodel_name or len(value) > 1):
                raise ValueError("Wrong value for %s: %r" % (self, value))
            id_ = value._ids[0] if value._ids else None
        elif isinstance(value, tuple):
            # value is either a pair (id, name), or a tuple of ids
            id_ = value[0] if value else None
        elif isinstance(value, dict):
            # return a new record (with the given field 'id' as origin)
            comodel = record.env[self.comodel_name]
            origin = comodel.browse(value.get('id'))
            id_ = comodel.new(value, origin=origin).id
        else:
            id_ = None

        if self.delegate and record and not any(record._ids):
            # if all records are new, then so is the parent
            id_ = id_ and NewId(id_)

        return id_

    def convert_to_record(self, value, record):
        # use registry to avoid creating a recordset for the model
        ids = () if value is None else (value,)
        prefetch_ids = PrefetchMany2one(record, self)
        return record.pool[self.comodel_name](record.env, ids, prefetch_ids)

    def convert_to_record_multi(self, values, records):
        # return the ids as a recordset without duplicates
        prefetch_ids = PrefetchMany2one(records, self)
        ids = tuple(unique(id_ for id_ in values if id_ is not None))
        return records.pool[self.comodel_name](records.env, ids, prefetch_ids)

    def convert_to_read(self, value, record, use_display_name=True):
        if use_display_name and value:
            # evaluate display_name as superuser, because the visibility of a
            # many2one field value (id and name) depends on the current record's
            # access rights, and not the value's access rights.
            try:
                # performance: value.sudo() prefetches the same records as value
                return (value.id, value.sudo().display_name)
            except MissingError:
                # Should not happen, unless the foreign key is missing.
                return False
        else:
            return value.id

    def convert_to_write(self, value, record):
        if type(value) is int or type(value) is NewId:
            return value
        if not value:
            return False
        if isinstance(value, BaseModel) and value._name == self.comodel_name:
            return value.id
        if isinstance(value, tuple):
            # value is either a pair (id, name), or a tuple of ids
            return value[0] if value else False
        if isinstance(value, dict):
            return record.env[self.comodel_name].new(value).id
        raise ValueError("Wrong value for %s: %r" % (self, value))

    def convert_to_export(self, value, record):
        return value.display_name if value else ''

    def convert_to_display_name(self, value, record):
        return value.display_name

    def write(self, records, value):
        # discard recomputation of self on records
        records.env.remove_to_compute(self, records)

        # discard the records that are not modified
        cache = records.env.cache
        cache_value = self.convert_to_cache(value, records)
        records = cache.get_records_different_from(records, self, cache_value)
        if not records:
            return

        # remove records from the cache of one2many fields of old corecords
        self._remove_inverses(records, cache_value)

        # update the cache of self
        dirty = self.store and any(records._ids)
        cache.update(records, self, itertools.repeat(cache_value), dirty=dirty)

        # update the cache of one2many fields of new corecord
        self._update_inverses(records, cache_value)

    def _remove_inverses(self, records, value):
        """ Remove `records` from the cached values of the inverse fields of `self`. """
        cache = records.env.cache
        record_ids = set(records._ids)

        # align(id) returns a NewId if records are new, a real id otherwise
        align = (lambda id_: id_) if all(record_ids) else (lambda id_: id_ and NewId(id_))

        for invf in records.pool.field_inverses[self]:
            corecords = records.env[self.comodel_name].browse(
                align(id_) for id_ in cache.get_values(records, self)
            )
            for corecord in corecords:
                ids0 = cache.get(corecord, invf, None)
                if ids0 is not None:
                    ids1 = tuple(id_ for id_ in ids0 if id_ not in record_ids)
                    cache.set(corecord, invf, ids1)

    def _update_inverses(self, records, value):
        """ Add `records` to the cached values of the inverse fields of `self`. """
        if value is None:
            return
        cache = records.env.cache
        corecord = self.convert_to_record(value, records)
        for invf in records.pool.field_inverses[self]:
            valid_records = records.filtered_domain(invf.get_domain_list(corecord))
            if not valid_records:
                continue
            ids0 = cache.get(corecord, invf, None)
            # if the value for the corecord is not in cache, but this is a new
            # record, assign it anyway, as you won't be able to fetch it from
            # database (see `test_sale_order`)
            if ids0 is not None or not corecord.id:
                ids1 = tuple(unique((ids0 or ()) + valid_records._ids))
                cache.set(corecord, invf, ids1)

    def condition_to_sql(self, field_expr: str, operator: str, value, model: BaseModel, alias: str, query: Query) -> SQL:
        if operator not in ('any', 'not any') or field_expr != self.name:
            # for other operators than 'any', just generate condition based on column type
            return super().condition_to_sql(field_expr, operator, value, model, alias, query)

        fname = field_expr
        comodel = model.env[self.comodel_name]
        sql_field = model._field_to_sql(alias, fname, query)

        if not isinstance(value, Domain):
            # value is SQL or Query
            if isinstance(value, Query):
                subselect = value.subselect()
            elif isinstance(value, SQL):
                subselect = SQL("(%s)", value)
            else:
                raise TypeError(f"condition_to_sql() 'any' operator accepts Domain, SQL or Query, got {value}")
            sql = SQL(
                "%s%s%s",
                sql_field,
                SQL(" IN ") if operator == 'any' else SQL(" NOT IN "),
                subselect,
            )
            if not self.required and operator != 'any':
                sql = SQL("(%s OR %s IS NULL)", sql, sql_field)
            if self.company_dependent:
                sql = self._condition_to_sql_company(sql, field_expr, operator, value, model, alias, query)
            return sql

        # value is a Domain

        if self.auto_join:
            coalias = query.make_alias(alias, self.name)
            # auto_join bypasses checks to join the field
            # for the comodel, the access is not bypassed
            query.add_join('LEFT JOIN', coalias, comodel._table, SQL(
                "%s = %s",
                sql_field,
                SQL.identifier(coalias, 'id'),
            ))

            if operator == 'not any':
                sql = value._to_sql(comodel, coalias, query)
                return SQL("(%s IS NULL OR (%s) IS NOT TRUE)", sql_field, sql)
            return value._to_sql(comodel, coalias, query)

        # execute search and generate condition with a SQL query
        domain_query = comodel.with_context(active_test=False)._search(value)
        return self.condition_to_sql(fname, operator, domain_query, model, alias, query)


class _RelationalMulti(_Relational[M], typing.Generic[M]):
    r"Abstract class for relational fields \*2many."
    write_sequence = 20

    # Important: the cache contains the ids of all the records in the relation,
    # including inactive records.  Inactive records are filtered out by
    # convert_to_record(), depending on the context.

    def _update(self, records, value):
        """ Update the cached value of ``self`` for ``records`` with ``value``. """
        records.env.cache.patch(records, self, value.id)
        records.modified([self.name])

    def convert_to_cache(self, value, record, validate=True):
        # cache format: tuple(ids)
        if isinstance(value, BaseModel):
            if validate and value._name != self.comodel_name:
                raise ValueError("Wrong value for %s: %s" % (self, value))
            ids = value._ids
            if record and not record.id:
                # x2many field value of new record is new records
                ids = tuple(it and NewId(it) for it in ids)
            return ids

        elif isinstance(value, (list, tuple)):
            # value is a list/tuple of commands, dicts or record ids
            comodel = record.env[self.comodel_name]
            # if record is new, the field's value is new records
            if record and not record.id:
                browse = lambda it: comodel.browse((it and NewId(it),))
            else:
                browse = comodel.browse
            # determine the value ids: in case of a real record or a new record
            # with origin, take its current value
            ids = OrderedSet(record[self.name]._ids if record._origin else ())
            # modify ids with the commands
            for command in value:
                if isinstance(command, (tuple, list)):
                    if command[0] == Command.CREATE:
                        ids.add(comodel.new(command[2], ref=command[1]).id)
                    elif command[0] == Command.UPDATE:
                        line = browse(command[1])
                        if validate:
                            line.update(command[2])
                        else:
                            line._update_cache(command[2], validate=False)
                        ids.add(line.id)
                    elif command[0] in (Command.DELETE, Command.UNLINK):
                        ids.discard(browse(command[1]).id)
                    elif command[0] == Command.LINK:
                        ids.add(browse(command[1]).id)
                    elif command[0] == Command.CLEAR:
                        ids.clear()
                    elif command[0] == Command.SET:
                        ids = OrderedSet(browse(it).id for it in command[2])
                elif isinstance(command, dict):
                    ids.add(comodel.new(command).id)
                else:
                    ids.add(browse(command).id)
            # return result as a tuple
            return tuple(ids)

        elif not value:
            return ()

        raise ValueError("Wrong value for %s: %s" % (self, value))

    def convert_to_record(self, value, record):
        # use registry to avoid creating a recordset for the model
        prefetch_ids = PrefetchX2many(record, self)
        Comodel = record.pool[self.comodel_name]
        corecords = Comodel(record.env, value, prefetch_ids)
        if (
            Comodel._active_name
            and self.context.get('active_test', record.env.context.get('active_test', True))
        ):
            corecords = corecords.filtered(Comodel._active_name).with_prefetch(prefetch_ids)
        return corecords

    def convert_to_record_multi(self, values, records):
        # return the list of ids as a recordset without duplicates
        prefetch_ids = PrefetchX2many(records, self)
        Comodel = records.pool[self.comodel_name]
        ids = tuple(unique(id_ for ids in values for id_ in ids))
        corecords = Comodel(records.env, ids, prefetch_ids)
        if (
            Comodel._active_name
            and self.context.get('active_test', records.env.context.get('active_test', True))
        ):
            corecords = corecords.filtered(Comodel._active_name).with_prefetch(prefetch_ids)
        return corecords

    def convert_to_read(self, value, record, use_display_name=True):
        return value.ids

    def convert_to_write(self, value, record):
        if isinstance(value, tuple):
            # a tuple of ids, this is the cache format
            value = record.env[self.comodel_name].browse(value)

        if isinstance(value, BaseModel) and value._name == self.comodel_name:
            def get_origin(val):
                return val._origin if isinstance(val, BaseModel) else val

            # make result with new and existing records
            inv_names = {field.name for field in record.pool.field_inverses[self]}
            result = [Command.set([])]
            for record in value:
                origin = record._origin
                if not origin:
                    values = record._convert_to_write({
                        name: record[name]
                        for name in record._cache
                        if name not in inv_names
                    })
                    result.append(Command.create(values))
                else:
                    result[0][2].append(origin.id)
                    if record != origin:
                        values = record._convert_to_write({
                            name: record[name]
                            for name in record._cache
                            if name not in inv_names and get_origin(record[name]) != origin[name]
                        })
                        if values:
                            result.append(Command.update(origin.id, values))
            return result

        if value is False or value is None:
            return [Command.clear()]

        if isinstance(value, list):
            return value

        raise ValueError("Wrong value for %s: %s" % (self, value))

    def convert_to_export(self, value, record):
        return ','.join(value.mapped('display_name')) if value else ''

    def convert_to_display_name(self, value, record):
        raise NotImplementedError()

    def get_depends(self, model):
        depends, depends_context = super().get_depends(model)
        if not self.compute and isinstance(self.domain, list):
            depends = unique(itertools.chain(depends, (
                self.name + '.' + arg[0]
                for arg in self.domain
                if isinstance(arg, (tuple, list)) and isinstance(arg[0], str)
            )))
        return depends, depends_context

    def create(self, record_values):
        """ Write the value of ``self`` on the given records, which have just
        been created.

        :param record_values: a list of pairs ``(record, value)``, where
            ``value`` is in the format of method :meth:`BaseModel.write`
        """
        self.write_batch(record_values, True)

    def write(self, records, value):
        # discard recomputation of self on records
        records.env.remove_to_compute(self, records)
        self.write_batch([(records, value)])

    def write_batch(self, records_commands_list, create=False):
        if not records_commands_list:
            return

        for idx, (recs, value) in enumerate(records_commands_list):
            if isinstance(value, tuple):
                value = [Command.set(value)]
            elif isinstance(value, BaseModel) and value._name == self.comodel_name:
                value = [Command.set(value._ids)]
            elif value is False or value is None:
                value = [Command.clear()]
            elif isinstance(value, list) and value and not isinstance(value[0], (tuple, list)):
                value = [Command.set(tuple(value))]
            if not isinstance(value, list):
                raise ValueError("Wrong value for %s: %s" % (self, value))
            records_commands_list[idx] = (recs, value)

        record_ids = {rid for recs, cs in records_commands_list for rid in recs._ids}
        if all(record_ids):
            self.write_real(records_commands_list, create)
        else:
            assert not any(record_ids), f"{records_commands_list} contains a mix of real and new records. It is not supported."
            self.write_new(records_commands_list)

    def _check_sudo_commands(self, comodel):
        # if the model doesn't accept sudo commands
        if not comodel._allow_sudo_commands:
            # Then, disable sudo and reset the transaction origin user
            return comodel.sudo(False).with_user(comodel.env.transaction.default_env.uid)
        return comodel

    def condition_to_sql(self, field_expr: str, operator: str, value, model: BaseModel, alias: str, query: Query) -> SQL:
        assert field_expr == self.name, "Supporting condition only to field"
        model._check_field_access(self, 'read')
        comodel = model.env[self.comodel_name]

        # update the operator to 'any'
        if operator in ('=', '!='):
            operator = 'in' if operator == '=' else 'not in'
            value = [value]
        if operator in ('in', 'not in'):
            operator = 'any' if operator == 'in' else 'not any'
        assert operator in ('any', 'not any'), \
            f"Relational field {self} expects 'any' operator"
        exists = operator == 'any'

        # check the value and execute the query
        if isinstance(value, COLLECTION_TYPES):
            value = OrderedSet(value)
            comodel = comodel.sudo().with_context(active_test=False)
            # If there are nulls to be checked, the condition is inversed.
            #  in (False, 1) => not any (id not in (1))
            #  not in (False, 1) => any (id not in {1})
            if False in value:
                exists = not exists
                ids_domain = Domain('id', 'not in', value - {False})
                value = comodel._search(ids_domain)
            else:
                value = comodel.browse(value)._as_query(ordered=False)
        elif isinstance(value, SQL):
            # wrap SQL into a simple query
            comodel = comodel.sudo()
            value = Domain('id', 'any', value)
        coquery = self._get_query_for_condition_value(model, comodel, value)
        return self._condition_to_sql_relational(model, alias, exists, coquery, query)

    def _get_query_for_condition_value(self, model: BaseModel, comodel: BaseModel, value: Domain | Query) -> Query:
        """ Return Query run on the comodel with the field.domain injected."""
        field_domain = Domain(self.get_domain_list(model))
        if isinstance(value, Domain):
            domain = value & field_domain
            comodel = comodel.with_context(**self.context)
            if self.auto_join:
                # bypass access rules for auto-join
                query = comodel._where_calc(domain)
            else:
                query = comodel._search(domain)
            assert isinstance(query, Query)
            return query
        if isinstance(value, Query):
            # add the field_domain to the query
            domain = field_domain._optimize(comodel)
            if not domain.is_true():
                # TODO should clone/copy Query value
                value.add_where(domain._to_sql(comodel, value.table, value))
            return value
        raise NotImplementedError(f"Cannot build query for {value}")

    def _condition_to_sql_relational(self, model: BaseModel, alias: str, exists: bool, coquery: Query, query: Query) -> SQL:
        raise NotImplementedError


class One2many(_RelationalMulti[M]):
    """One2many field; the value of such a field is the recordset of all the
    records in ``comodel_name`` such that the field ``inverse_name`` is equal to
    the current record.

    :param str comodel_name: name of the target model

    :param str inverse_name: name of the inverse ``Many2one`` field in
        ``comodel_name``

    :param domain: an optional domain to set on candidate values on the
        client side (domain or a python expression that will be evaluated
        to provide domain)

    :param dict context: an optional context to use on the client side when
        handling that field

    :param bool auto_join: whether JOINs are generated upon search through that
        field (default: ``False``)

    The attributes ``comodel_name`` and ``inverse_name`` are mandatory except in
    the case of related fields or field extensions.
    """
    type = 'one2many'

    inverse_name = None                 # name of the inverse field
    copy = False                        # o2m are not copied by default

    def __init__(self, comodel_name: str | Sentinel = SENTINEL, inverse_name: str | Sentinel = SENTINEL,
                 string: str | Sentinel = SENTINEL, **kwargs):
        super(One2many, self).__init__(
            comodel_name=comodel_name,
            inverse_name=inverse_name,
            string=string,
            **kwargs
        )

    def setup_nonrelated(self, model):
        super(One2many, self).setup_nonrelated(model)
        if self.inverse_name:
            # link self to its inverse field and vice-versa
            comodel = model.env[self.comodel_name]
            try:
                invf = comodel._fields[self.inverse_name]
            except KeyError:
                raise ValueError(f"{self.inverse_name!r} declared in {self!r} does not exist on {comodel._name!r}.")
            if isinstance(invf, (Many2one, Many2oneReference)):
                # setting one2many fields only invalidates many2one inverses;
                # integer inverses (res_model/res_id pairs) are not supported
                model.pool.field_inverses.add(self, invf)
            comodel.pool.field_inverses.add(invf, self)

    _description_relation_field = property(attrgetter('inverse_name'))

    def update_db(self, model, columns):
        if self.comodel_name in model.env:
            comodel = model.env[self.comodel_name]
            if self.inverse_name not in comodel._fields:
                raise UserError(model.env._(
                    'No inverse field "%(inverse_field)s" found for "%(comodel)s"',
                    inverse_field=self.inverse_name,
                    comodel=self.comodel_name
                ))

    def get_domain_list(self, records):
        comodel = records.env.registry[self.comodel_name]
        inverse_field = comodel._fields[self.inverse_name]
        domain = super(One2many, self).get_domain_list(records)
        if inverse_field.type == 'many2one_reference':
            domain = domain + [(inverse_field.model_field, '=', records._name)]
        return domain

    def __get__(self, records, owner=None):
        if records is not None and self.inverse_name is not None:
            # force the computation of the inverse field to ensure that the
            # cache value of self is consistent
            inverse_field = records.pool[self.comodel_name]._fields[self.inverse_name]
            if inverse_field.compute:
                records.env[self.comodel_name]._recompute_model([self.inverse_name])
        return super().__get__(records, owner)

    def read(self, records):
        # retrieve the lines in the comodel
        context = {'active_test': False}
        context.update(self.context)
        comodel = records.env[self.comodel_name].with_context(**context)
        inverse = self.inverse_name
        inverse_field = comodel._fields[inverse]

        # optimization: fetch the inverse and active fields with search()
        domain = self.get_domain_list(records) + [(inverse, 'in', records.ids)]
        field_names = [inverse]
        if comodel._active_name:
            field_names.append(comodel._active_name)
        lines = comodel.search_fetch(domain, field_names)

        # group lines by inverse field (without prefetching other fields)
        get_id = (lambda rec: rec.id) if inverse_field.type == 'many2one' else int
        group = defaultdict(list)
        for line in lines:
            # line[inverse] may be a record or an integer
            group[get_id(line[inverse])].append(line.id)

        # store result in cache
        values = [tuple(group[id_]) for id_ in records._ids]
        records.env.cache.insert_missing(records, self, values)

    def write_real(self, records_commands_list, create=False):
        """ Update real records. """
        # records_commands_list = [(records, commands), ...]
        if not records_commands_list:
            return

        model = records_commands_list[0][0].browse()
        comodel = model.env[self.comodel_name].with_context(**self.context)
        comodel = self._check_sudo_commands(comodel)

        if self.store:
            inverse = self.inverse_name
            to_create = []                      # line vals to create
            to_delete = []                      # line ids to delete
            to_link = defaultdict(OrderedSet)   # {record: line_ids}
            allow_full_delete = not create

            def unlink(lines):
                if getattr(comodel._fields[inverse], 'ondelete', False) == 'cascade':
                    to_delete.extend(lines._ids)
                else:
                    lines[inverse] = False

            def flush():
                if to_link:
                    before = {record: record[self.name] for record in to_link}
                if to_delete:
                    # unlink() will remove the lines from the cache
                    comodel.browse(to_delete).unlink()
                    to_delete.clear()
                if to_create:
                    # create() will add the new lines to the cache of records
                    comodel.create(to_create)
                    to_create.clear()
                if to_link:
                    for record, line_ids in to_link.items():
                        lines = comodel.browse(line_ids) - before[record]
                        # linking missing lines should fail
                        lines.mapped(inverse)
                        lines[inverse] = record
                    to_link.clear()

            for recs, commands in records_commands_list:
                for command in (commands or ()):
                    if command[0] == Command.CREATE:
                        for record in recs:
                            to_create.append(dict(command[2], **{inverse: record.id}))
                        allow_full_delete = False
                    elif command[0] == Command.UPDATE:
                        prefetch_ids = recs[self.name]._prefetch_ids
                        comodel.browse(command[1]).with_prefetch(prefetch_ids).write(command[2])
                    elif command[0] == Command.DELETE:
                        to_delete.append(command[1])
                    elif command[0] == Command.UNLINK:
                        unlink(comodel.browse(command[1]))
                    elif command[0] == Command.LINK:
                        to_link[recs[-1]].add(command[1])
                        allow_full_delete = False
                    elif command[0] in (Command.CLEAR, Command.SET):
                        line_ids = command[2] if command[0] == Command.SET else []
                        if not allow_full_delete:
                            # do not try to delete anything in creation mode if nothing has been created before
                            if line_ids:
                                # equivalent to Command.LINK
                                if line_ids.__class__ is int:
                                    line_ids = [line_ids]
                                to_link[recs[-1]].update(line_ids)
                                allow_full_delete = False
                            continue
                        flush()
                        # assign the given lines to the last record only
                        lines = comodel.browse(line_ids)
                        domain = self.get_domain_list(model) + \
                            [(inverse, 'in', recs.ids), ('id', 'not in', lines.ids)]
                        unlink(comodel.search(domain))
                        lines[inverse] = recs[-1]

            flush()

        else:
            ids = OrderedSet(rid for recs, cs in records_commands_list for rid in recs._ids)
            records = records_commands_list[0][0].browse(ids)
            cache = records.env.cache

            def link(record, lines):
                ids = record[self.name]._ids
                cache.set(record, self, tuple(unique(ids + lines._ids)))

            def unlink(lines):
                for record in records:
                    cache.set(record, self, (record[self.name] - lines)._ids)

            for recs, commands in records_commands_list:
                for command in (commands or ()):
                    if command[0] == Command.CREATE:
                        for record in recs:
                            link(record, comodel.new(command[2], ref=command[1]))
                    elif command[0] == Command.UPDATE:
                        comodel.browse(command[1]).write(command[2])
                    elif command[0] == Command.DELETE:
                        unlink(comodel.browse(command[1]))
                    elif command[0] == Command.UNLINK:
                        unlink(comodel.browse(command[1]))
                    elif command[0] == Command.LINK:
                        link(recs[-1], comodel.browse(command[1]))
                    elif command[0] in (Command.CLEAR, Command.SET):
                        # assign the given lines to the last record only
                        cache.update(recs, self, itertools.repeat(()))
                        lines = comodel.browse(command[2] if command[0] == Command.SET else [])
                        cache.set(recs[-1], self, lines._ids)

    def write_new(self, records_commands_list):
        if not records_commands_list:
            return

        model = records_commands_list[0][0].browse()
        cache = model.env.cache
        comodel = model.env[self.comodel_name].with_context(**self.context)
        comodel = self._check_sudo_commands(comodel)

        ids = {record.id for records, _ in records_commands_list for record in records}
        records = model.browse(ids)

        def browse(ids):
            return comodel.browse([id_ and NewId(id_) for id_ in ids])

        # make sure self is in cache
        records[self.name]

        if self.store:
            inverse = self.inverse_name

            # make sure self's inverse is in cache
            inverse_field = comodel._fields[inverse]
            for record in records:
                cache.update(record[self.name], inverse_field, itertools.repeat(record.id))

            for recs, commands in records_commands_list:
                for command in commands:
                    if command[0] == Command.CREATE:
                        for record in recs:
                            line = comodel.new(command[2], ref=command[1])
                            line[inverse] = record
                    elif command[0] == Command.UPDATE:
                        browse([command[1]]).update(command[2])
                    elif command[0] == Command.DELETE:
                        browse([command[1]])[inverse] = False
                    elif command[0] == Command.UNLINK:
                        browse([command[1]])[inverse] = False
                    elif command[0] == Command.LINK:
                        browse([command[1]])[inverse] = recs[-1]
                    elif command[0] == Command.CLEAR:
                        cache.update(recs, self, itertools.repeat(()))
                    elif command[0] == Command.SET:
                        # assign the given lines to the last record only
                        cache.update(recs, self, itertools.repeat(()))
                        last, lines = recs[-1], browse(command[2])
                        cache.set(last, self, lines._ids)
                        cache.update(lines, inverse_field, itertools.repeat(last.id))

        else:
            def link(record, lines):
                ids = record[self.name]._ids
                cache.set(record, self, tuple(unique(ids + lines._ids)))

            def unlink(lines):
                for record in records:
                    cache.set(record, self, (record[self.name] - lines)._ids)

            for recs, commands in records_commands_list:
                for command in commands:
                    if command[0] == Command.CREATE:
                        for record in recs:
                            link(record, comodel.new(command[2], ref=command[1]))
                    elif command[0] == Command.UPDATE:
                        browse([command[1]]).update(command[2])
                    elif command[0] == Command.DELETE:
                        unlink(browse([command[1]]))
                    elif command[0] == Command.UNLINK:
                        unlink(browse([command[1]]))
                    elif command[0] == Command.LINK:
                        link(recs[-1], browse([command[1]]))
                    elif command[0] in (Command.CLEAR, Command.SET):
                        # assign the given lines to the last record only
                        cache.update(recs, self, itertools.repeat(()))
                        lines = browse(command[2] if command[0] == Command.SET else [])
                        cache.set(recs[-1], self, lines._ids)

    def _get_query_for_condition_value(self, model: BaseModel, comodel: BaseModel, value) -> Query:
        inverse_field = comodel._fields[self.inverse_name]
        if not inverse_field.required:
            # In the condition, one must avoid subqueries to return
            # NULL values, since it makes the IN test NULL instead
            # of FALSE.  This may discard expected results, as for
            # instance "id NOT IN (42, NULL)" is never TRUE.
            if isinstance(value, Domain):
                value &= Domain(inverse_field.name, 'not in', {False})
            else:
                coquery = super()._get_query_for_condition_value(model, comodel, value)
                coquery.add_where(SQL(
                    "%s IS NOT NULL",
                    comodel._field_to_sql(coquery.table, inverse_field.name, coquery),
                ))
                return coquery
        return super()._get_query_for_condition_value(model, comodel, value)

    def _condition_to_sql_relational(self, model: BaseModel, alias: str, exists: bool, coquery: Query, query: Query) -> SQL:
        if coquery.is_empty():
            return Domain(not exists)._to_sql(model, alias, query)

        comodel = model.env[self.comodel_name].sudo()
        inverse_field = comodel._fields[self.inverse_name]
        if inverse_field.store:
            subselect = coquery.subselect(
                comodel._field_to_sql(coquery.table, inverse_field.name, coquery)
            )
        else:
            # determine ids1 in model related to ids2
            # TODO should we support this in the future?
            recs = comodel.browse(coquery).with_context(prefetch_fields=False)
            if inverse_field.relational:
                inverses = inverse_field.__get__(recs)
            else:
                # int values, map them
                inverses = model.browse(inverse_field.__get__(rec) for rec in recs)
            subselect = inverses._as_query(ordered=False).subselect()

        return SQL(
            "%s%s%s",
            SQL.identifier(alias, 'id'),
            SQL_OPERATORS['in' if exists else 'not in'],
            subselect,
        )


class Many2many(_RelationalMulti[M]):
    """ Many2many field; the value of such a field is the recordset.

    :param comodel_name: name of the target model (string)
        mandatory except in the case of related or extended fields

    :param str relation: optional name of the table that stores the relation in
        the database

    :param str column1: optional name of the column referring to "these" records
        in the table ``relation``

    :param str column2: optional name of the column referring to "those" records
        in the table ``relation``

    The attributes ``relation``, ``column1`` and ``column2`` are optional.
    If not given, names are automatically generated from model names,
    provided ``model_name`` and ``comodel_name`` are different!

    Note that having several fields with implicit relation parameters on a
    given model with the same comodel is not accepted by the ORM, since
    those field would use the same table. The ORM prevents two many2many
    fields to use the same relation parameters, except if

    - both fields use the same model, comodel, and relation parameters are
      explicit; or

    - at least one field belongs to a model with ``_auto = False``.

    :param domain: an optional domain to set on candidate values on the
        client side (domain or a python expression that will be evaluated
        to provide domain)

    :param dict context: an optional context to use on the client side when
        handling that field

    :param bool check_company: Mark the field to be verified in
        :meth:`~odoo.models.Model._check_company`. Add a default company
        domain depending on the field attributes.

    """
    type = 'many2many'

    _explicit = True                    # whether schema is explicitly given
    relation = None                     # name of table
    column1 = None                      # column of table referring to model
    column2 = None                      # column of table referring to comodel
    ondelete = 'cascade'                # optional ondelete for the column2 fkey

    def __init__(self, comodel_name: str | Sentinel = SENTINEL, relation: str | Sentinel = SENTINEL,
                 column1: str | Sentinel = SENTINEL, column2: str | Sentinel = SENTINEL,
                 string: str | Sentinel = SENTINEL, **kwargs):
        if 'auto_join' in kwargs:
            raise NotImplementedError("auto_join is not supported on Many2many fields")
        super(Many2many, self).__init__(
            comodel_name=comodel_name,
            relation=relation,
            column1=column1,
            column2=column2,
            string=string,
            **kwargs
        )

    def setup_nonrelated(self, model):
        super().setup_nonrelated(model)
        # 2 cases:
        # 1) The ondelete attribute is defined and its definition makes sense
        # 2) The ondelete attribute is explicitly defined as 'set null' for a m2m,
        #    this is considered a programming error.
        if self.ondelete not in ('cascade', 'restrict'):
            raise ValueError(
                "The m2m field %s of model %s declares its ondelete policy "
                "as being %r. Only 'restrict' and 'cascade' make sense."
                % (self.name, model._name, self.ondelete)
            )
        if self.store:
            if not (self.relation and self.column1 and self.column2):
                if not self.relation:
                    self._explicit = False
                # table name is based on the stable alphabetical order of tables
                comodel = model.env[self.comodel_name]
                if not self.relation:
                    tables = sorted([model._table, comodel._table])
                    assert tables[0] != tables[1], \
                        "%s: Implicit/canonical naming of many2many relationship " \
                        "table is not possible when source and destination models " \
                        "are the same" % self
                    self.relation = '%s_%s_rel' % tuple(tables)
                if not self.column1:
                    self.column1 = '%s_id' % model._table
                if not self.column2:
                    self.column2 = '%s_id' % comodel._table
            # check validity of table name
            check_pg_name(self.relation)
        else:
            self.relation = self.column1 = self.column2 = None

        if self.relation:
            m2m = model.pool._m2m

            # check whether other fields use the same schema
            fields = m2m[(self.relation, self.column1, self.column2)]
            for field in fields:
                if (    # same model: relation parameters must be explicit
                    self.model_name == field.model_name and
                    self.comodel_name == field.comodel_name and
                    self._explicit and field._explicit
                ) or (  # different models: one model must be _auto=False
                    self.model_name != field.model_name and
                    not (model._auto and model.env[field.model_name]._auto)
                ):
                    continue
                msg = "Many2many fields %s and %s use the same table and columns"
                raise TypeError(msg % (self, field))
            fields.append(self)

            # retrieve inverse fields, and link them in field_inverses
            for field in m2m[(self.relation, self.column2, self.column1)]:
                model.pool.field_inverses.add(self, field)
                model.pool.field_inverses.add(field, self)

    def update_db(self, model, columns):
        cr = model._cr
        # Do not reflect relations for custom fields, as they do not belong to a
        # module. They are automatically removed when dropping the corresponding
        # 'ir.model.field'.
        if not self.manual:
            model.pool.post_init(model.env['ir.model.relation']._reflect_relation,
                                 model, self.relation, self._module)
        comodel = model.env[self.comodel_name]
        if not sql.table_exists(cr, self.relation):
            cr.execute(SQL(
                """ CREATE TABLE %(rel)s (%(id1)s INTEGER NOT NULL,
                                          %(id2)s INTEGER NOT NULL,
                                          PRIMARY KEY(%(id1)s, %(id2)s));
                    COMMENT ON TABLE %(rel)s IS %(comment)s;
                    CREATE INDEX ON %(rel)s (%(id2)s, %(id1)s); """,
                rel=SQL.identifier(self.relation),
                id1=SQL.identifier(self.column1),
                id2=SQL.identifier(self.column2),
                comment=f"RELATION BETWEEN {model._table} AND {comodel._table}",
            ))
            _schema.debug("Create table %r: m2m relation between %r and %r", self.relation, model._table, comodel._table)
            model.pool.post_init(self.update_db_foreign_keys, model)
            return True

        model.pool.post_init(self.update_db_foreign_keys, model)

    def update_db_foreign_keys(self, model):
        """ Add the foreign keys corresponding to the field's relation table. """
        comodel = model.env[self.comodel_name]
        if model._is_an_ordinary_table():
            model.pool.add_foreign_key(
                self.relation, self.column1, model._table, 'id', 'cascade',
                model, self._module, force=False,
            )
        if comodel._is_an_ordinary_table():
            model.pool.add_foreign_key(
                self.relation, self.column2, comodel._table, 'id', self.ondelete,
                model, self._module,
            )

    def read(self, records):
        context = {'active_test': False}
        context.update(self.context)
        comodel = records.env[self.comodel_name].with_context(**context)

        # make the query for the lines
        domain = self.get_domain_list(records)
        query = comodel._where_calc(domain)
        comodel._apply_ir_rules(query, 'read')
        query.order = comodel._order_to_sql(comodel._order, query)

        # join with many2many relation table
        sql_id1 = SQL.identifier(self.relation, self.column1)
        sql_id2 = SQL.identifier(self.relation, self.column2)
        query.add_join('JOIN', self.relation, None, SQL(
            "%s = %s", sql_id2, SQL.identifier(comodel._table, 'id'),
        ))
        query.add_where(SQL("%s IN %s", sql_id1, tuple(records.ids)))

        # retrieve pairs (record, line) and group by record
        group = defaultdict(list)
        for id1, id2 in records.env.execute_query(query.select(sql_id1, sql_id2)):
            group[id1].append(id2)

        # store result in cache
        values = [tuple(group[id_]) for id_ in records._ids]
        records.env.cache.insert_missing(records, self, values)

    def write_real(self, records_commands_list, create=False):
        # records_commands_list = [(records, commands), ...]
        if not records_commands_list:
            return

        model = records_commands_list[0][0].browse()
        comodel = model.env[self.comodel_name].with_context(**self.context)
        comodel = self._check_sudo_commands(comodel)
        cr = model.env.cr

        # determine old and new relation {x: ys}
        set = OrderedSet
        ids = set(rid for recs, cs in records_commands_list for rid in recs.ids)
        records = model.browse(ids)

        if self.store:
            # Using `record[self.name]` generates 2 SQL queries when the value
            # is not in cache: one that actually checks access rules for
            # records, and the other one fetching the actual data. We use
            # `self.read` instead to shortcut the first query.
            missing_ids = list(records.env.cache.get_missing_ids(records, self))
            if missing_ids:
                self.read(records.browse(missing_ids))

        # determine new relation {x: ys}
        old_relation = {record.id: set(record[self.name]._ids) for record in records}
        new_relation = {x: set(ys) for x, ys in old_relation.items()}

        # operations on new relation
        def relation_add(xs, y):
            for x in xs:
                new_relation[x].add(y)

        def relation_remove(xs, y):
            for x in xs:
                new_relation[x].discard(y)

        def relation_set(xs, ys):
            for x in xs:
                new_relation[x] = set(ys)

        def relation_delete(ys):
            # the pairs (x, y) have been cascade-deleted from relation
            for ys1 in old_relation.values():
                ys1 -= ys
            for ys1 in new_relation.values():
                ys1 -= ys

        for recs, commands in records_commands_list:
            to_create = []  # line vals to create
            to_delete = []  # line ids to delete
            for command in (commands or ()):
                if not isinstance(command, (list, tuple)) or not command:
                    continue
                if command[0] == Command.CREATE:
                    to_create.append((recs._ids, command[2]))
                elif command[0] == Command.UPDATE:
                    prefetch_ids = recs[self.name]._prefetch_ids
                    comodel.browse(command[1]).with_prefetch(prefetch_ids).write(command[2])
                elif command[0] == Command.DELETE:
                    to_delete.append(command[1])
                elif command[0] == Command.UNLINK:
                    relation_remove(recs._ids, command[1])
                elif command[0] == Command.LINK:
                    relation_add(recs._ids, command[1])
                elif command[0] in (Command.CLEAR, Command.SET):
                    # new lines must no longer be linked to records
                    to_create = [(set(ids) - set(recs._ids), vals) for (ids, vals) in to_create]
                    relation_set(recs._ids, command[2] if command[0] == Command.SET else ())

            if to_create:
                # create lines in batch, and link them
                lines = comodel.create([vals for ids, vals in to_create])
                for line, (ids, _vals) in zip(lines, to_create):
                    relation_add(ids, line.id)

            if to_delete:
                # delete lines in batch
                comodel.browse(to_delete).unlink()
                relation_delete(to_delete)

        # update the cache of self
        cache = records.env.cache
        for record in records:
            cache.set(record, self, tuple(new_relation[record.id]))

        # determine the corecords for which the relation has changed
        modified_corecord_ids = set()

        # process pairs to add (beware of duplicates)
        pairs = [(x, y) for x, ys in new_relation.items() for y in ys - old_relation[x]]
        if pairs:
            if self.store:
                cr.execute(SQL(
                    "INSERT INTO %s (%s, %s) VALUES %s ON CONFLICT DO NOTHING",
                    SQL.identifier(self.relation),
                    SQL.identifier(self.column1),
                    SQL.identifier(self.column2),
                    SQL(", ").join(pairs),
                ))

            # update the cache of inverse fields
            y_to_xs = defaultdict(set)
            for x, y in pairs:
                y_to_xs[y].add(x)
                modified_corecord_ids.add(y)
            for invf in records.pool.field_inverses[self]:
                domain = invf.get_domain_list(comodel)
                valid_ids = set(records.filtered_domain(domain)._ids)
                if not valid_ids:
                    continue
                for y, xs in y_to_xs.items():
                    corecord = comodel.browse(y)
                    try:
                        ids0 = cache.get(corecord, invf)
                        ids1 = tuple(set(ids0) | (xs & valid_ids))
                        cache.set(corecord, invf, ids1)
                    except KeyError:
                        pass

        # process pairs to remove
        pairs = [(x, y) for x, ys in old_relation.items() for y in ys - new_relation[x]]
        if pairs:
            y_to_xs = defaultdict(set)
            for x, y in pairs:
                y_to_xs[y].add(x)
                modified_corecord_ids.add(y)

            if self.store:
                # express pairs as the union of cartesian products:
                #    pairs = [(1, 11), (1, 12), (1, 13), (2, 11), (2, 12), (2, 14)]
                # -> y_to_xs = {11: {1, 2}, 12: {1, 2}, 13: {1}, 14: {2}}
                # -> xs_to_ys = {{1, 2}: {11, 12}, {2}: {14}, {1}: {13}}
                xs_to_ys = defaultdict(set)
                for y, xs in y_to_xs.items():
                    xs_to_ys[frozenset(xs)].add(y)
                # delete the rows where (id1 IN xs AND id2 IN ys) OR ...
                cr.execute(SQL(
                    "DELETE FROM %s WHERE %s",
                    SQL.identifier(self.relation),
                    SQL(" OR ").join(
                        SQL("%s IN %s AND %s IN %s",
                            SQL.identifier(self.column1), tuple(xs),
                            SQL.identifier(self.column2), tuple(ys))
                        for xs, ys in xs_to_ys.items()
                    ),
                ))

            # update the cache of inverse fields
            for invf in records.pool.field_inverses[self]:
                for y, xs in y_to_xs.items():
                    corecord = comodel.browse(y)
                    try:
                        ids0 = cache.get(corecord, invf)
                        ids1 = tuple(id_ for id_ in ids0 if id_ not in xs)
                        cache.set(corecord, invf, ids1)
                    except KeyError:
                        pass

        if modified_corecord_ids:
            # trigger the recomputation of fields that depend on the inverse
            # fields of self on the modified corecords
            corecords = comodel.browse(modified_corecord_ids)
            corecords.modified([
                invf.name
                for invf in model.pool.field_inverses[self]
                if invf.model_name == self.comodel_name
            ])

    def write_new(self, records_commands_list):
        """ Update self on new records. """
        if not records_commands_list:
            return

        model = records_commands_list[0][0].browse()
        comodel = model.env[self.comodel_name].with_context(**self.context)
        comodel = self._check_sudo_commands(comodel)
        new = lambda id_: id_ and NewId(id_)

        # determine old and new relation {x: ys}
        set = OrderedSet
        old_relation = {record.id: set(record[self.name]._ids) for records, _ in records_commands_list for record in records}
        new_relation = {x: set(ys) for x, ys in old_relation.items()}

        for recs, commands in records_commands_list:
            for command in commands:
                if not isinstance(command, (list, tuple)) or not command:
                    continue
                if command[0] == Command.CREATE:
                    line_id = comodel.new(command[2], ref=command[1]).id
                    for line_ids in new_relation.values():
                        line_ids.add(line_id)
                elif command[0] == Command.UPDATE:
                    line_id = new(command[1])
                    comodel.browse([line_id]).update(command[2])
                elif command[0] == Command.DELETE:
                    line_id = new(command[1])
                    for line_ids in new_relation.values():
                        line_ids.discard(line_id)
                elif command[0] == Command.UNLINK:
                    line_id = new(command[1])
                    for line_ids in new_relation.values():
                        line_ids.discard(line_id)
                elif command[0] == Command.LINK:
                    line_id = new(command[1])
                    for line_ids in new_relation.values():
                        line_ids.add(line_id)
                elif command[0] in (Command.CLEAR, Command.SET):
                    # new lines must no longer be linked to records
                    line_ids = command[2] if command[0] == Command.SET else ()
                    line_ids = set(new(line_id) for line_id in line_ids)
                    for id_ in recs._ids:
                        new_relation[id_] = set(line_ids)

        if new_relation == old_relation:
            return

        records = model.browse(old_relation)

        # update the cache of self
        cache = records.env.cache
        for record in records:
            cache.set(record, self, tuple(new_relation[record.id]))

        # determine the corecords for which the relation has changed
        modified_corecord_ids = set()

        # process pairs to add (beware of duplicates)
        pairs = [(x, y) for x, ys in new_relation.items() for y in ys - old_relation[x]]
        if pairs:
            # update the cache of inverse fields
            y_to_xs = defaultdict(set)
            for x, y in pairs:
                y_to_xs[y].add(x)
                modified_corecord_ids.add(y)
            for invf in records.pool.field_inverses[self]:
                domain = invf.get_domain_list(comodel)
                valid_ids = set(records.filtered_domain(domain)._ids)
                if not valid_ids:
                    continue
                for y, xs in y_to_xs.items():
                    corecord = comodel.browse([y])
                    try:
                        ids0 = cache.get(corecord, invf)
                        ids1 = tuple(set(ids0) | (xs & valid_ids))
                        cache.set(corecord, invf, ids1)
                    except KeyError:
                        pass

        # process pairs to remove
        pairs = [(x, y) for x, ys in old_relation.items() for y in ys - new_relation[x]]
        if pairs:
            # update the cache of inverse fields
            y_to_xs = defaultdict(set)
            for x, y in pairs:
                y_to_xs[y].add(x)
                modified_corecord_ids.add(y)
            for invf in records.pool.field_inverses[self]:
                for y, xs in y_to_xs.items():
                    corecord = comodel.browse([y])
                    try:
                        ids0 = cache.get(corecord, invf)
                        ids1 = tuple(id_ for id_ in ids0 if id_ not in xs)
                        cache.set(corecord, invf, ids1)
                    except KeyError:
                        pass

        if modified_corecord_ids:
            # trigger the recomputation of fields that depend on the inverse
            # fields of self on the modified corecords
            corecords = comodel.browse(modified_corecord_ids)
            corecords.modified([
                invf.name
                for invf in model.pool.field_inverses[self]
                if invf.model_name == self.comodel_name
            ])

    def _condition_to_sql_relational(self, model: BaseModel, alias: str, exists: bool, coquery: Query, query: Query) -> SQL:
        assert not self.auto_join, f"auto_join not implemented for many2many fields ({self})"
        rel_table, rel_id1, rel_id2 = self.relation, self.column1, self.column2
        rel_alias = query.make_alias(alias, self.name)
        if not coquery.where_clause:
            # case: no constraints on table and we have foreign keys
            # so we can inverse the operator and check against empty query
            coquery = model.browse()._as_query()
            exists = not exists
        if coquery.is_empty():
            return SQL(
                "%sEXISTS (SELECT 1 FROM %s AS %s WHERE %s = %s)",
                SQL("NOT ") if exists else SQL(),
                SQL.identifier(rel_table),
                SQL.identifier(rel_alias),
                SQL.identifier(rel_alias, rel_id1),
                SQL.identifier(alias, 'id'),
            )
        return SQL(
            "%sEXISTS (SELECT 1 FROM %s AS %s WHERE %s = %s AND %s IN %s)",
            SQL("NOT ") if not exists else SQL(),
            SQL.identifier(rel_table),
            SQL.identifier(rel_alias),
            SQL.identifier(rel_alias, rel_id1),
            SQL.identifier(alias, 'id'),
            SQL.identifier(rel_alias, rel_id2),
            coquery.subselect(),
        )


class PrefetchMany2one:
    """ Iterable for the values of a many2one field on the prefetch set of a given record. """
    __slots__ = 'record', 'field'

    def __init__(self, record, field):
        self.record = record
        self.field = field

    def __iter__(self):
        records = self.record.browse(self.record._prefetch_ids)
        ids = self.record.env.cache.get_values(records, self.field)
        return unique(id_ for id_ in ids if id_ is not None)

    def __reversed__(self):
        records = self.record.browse(reversed(self.record._prefetch_ids))
        ids = self.record.env.cache.get_values(records, self.field)
        return unique(id_ for id_ in ids if id_ is not None)


class PrefetchX2many:
    """ Iterable for the values of an x2many field on the prefetch set of a given record. """
    __slots__ = 'record', 'field'

    def __init__(self, record, field):
        self.record = record
        self.field = field

    def __iter__(self):
        records = self.record.browse(self.record._prefetch_ids)
        ids_list = self.record.env.cache.get_values(records, self.field)
        return unique(id_ for ids in ids_list for id_ in ids)

    def __reversed__(self):
        records = self.record.browse(reversed(self.record._prefetch_ids))
        ids_list = self.record.env.cache.get_values(records, self.field)
        return unique(id_ for ids in ids_list for id_ in ids)
