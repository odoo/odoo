from __future__ import annotations

import itertools
import logging
import typing
from collections import defaultdict
from collections.abc import Reversible
from operator import attrgetter

from odoo.exceptions import AccessError, MissingError, UserError
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

if typing.TYPE_CHECKING:
    from collections.abc import Sequence
    from odoo.tools.misc import Collector
    from .types import CommandValue, ContextType, DomainType, Environment, Registry

    OnDelete = typing.Literal['cascade', 'set null', 'restrict']

_schema = logging.getLogger('odoo.schema')


class _Relational(Field[BaseModel]):
    """ Abstract class for relational fields. """
    relational: typing.Literal[True] = True
    comodel_name: str
    domain: DomainType = []         # domain for searching values
    context: ContextType = {}       # context for searching values
    bypass_search_access: bool = False  # whether access rights are bypassed on the comodel
    check_company: bool = False

    def __get__(self, records: BaseModel, owner=None):
        # base case: do the regular access
        if records is None or len(records._ids) <= 1:
            return super().__get__(records, owner)

        records._check_field_access(self, 'read')

        # multi-record case
        if self.compute and self.store:
            self.recompute(records)

        # get the cache
        env = records.env
        field_cache = self._get_cache(env)

        # retrieve values in cache, and fetch missing ones
        vals = []
        for record_id in records._ids:
            try:
                vals.append(field_cache[record_id])
            except KeyError:
                if self.store and record_id and len(vals) < len(records) - PREFETCH_MAX:
                    # a lot of missing records, just fetch that field
                    remaining = records[len(vals):]
                    remaining.fetch([self.name])
                    # fetch does not raise MissingError, check value
                    if record_id not in field_cache:
                        raise MissingError("\n".join([
                            env._("Record does not exist or has been deleted."),
                            env._("(Record: %(record)s, User: %(user)s)", record=record_id, user=env.uid),
                        ])) from None
                else:
                    remaining = records.__class__(env, (record_id,), records._prefetch_ids)
                    super().__get__(remaining, owner)
                # we have the record now
                vals.append(field_cache[record_id])

        return self.convert_to_record_multi(vals, records)

    def _update_inverse(self, records: BaseModel, value: BaseModel):
        """ Update the cached value of ``self`` for ``records`` with ``value``. """
        raise NotImplementedError

    def convert_to_record_multi(self, values, records):
        """ Convert a list of (relational field) values from the cache format to
        the record format, for the sake of optimization.
        """
        raise NotImplementedError

    def setup_nonrelated(self, model):
        super().setup_nonrelated(model)
        assert self.comodel_name in model.pool, \
            f"Field {self} with unknown comodel_name {self.comodel_name or '???'!r}"

    def setup_inverses(self, registry: Registry, inverses: Collector[Field, Field]):
        """ Populate ``inverses`` with ``self`` and its inverse fields. """

    def get_comodel_domain(self, model: BaseModel) -> Domain:
        """ Return a domain from the domain attribute. """
        domain = self.domain
        if callable(domain):
            # the callable can return either a list, Domain or a string
            domain = domain(model)
        if not domain or isinstance(domain, str):
            # if we don't have a domain or
            # domain=str is used only for the client-side
            return Domain.TRUE
        return Domain(domain)

    @property
    def _related_domain(self) -> DomainType | None:
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

    def _description_domain(self, env: Environment) -> str | list:
        domain = self._internal_description_domain_raw(env)
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
                    self.model_name + '.' + self.name,
                ))
                return domain
            company_domain = env[self.comodel_name]._check_company_domain(companies=unquote(cids))
            if not field_to_check:
                return f"{company_domain} + {domain or []}"
            else:
                no_company_domain = env[self.comodel_name]._check_company_domain(companies='')
                return f"({field_to_check} and {company_domain} or {no_company_domain}) + ({domain or []})"
        return domain

    def _description_allow_hierachy_operators(self, env):
        """ Return if the child_of/parent_of makes sense on this field """
        comodel = env[self.comodel_name]
        return comodel._parent_name in comodel._fields

    def _internal_description_domain_raw(self, env) -> str | list:
        domain = self.domain
        if callable(domain):
            domain = domain(env[self.model_name])
        if isinstance(domain, Domain):
            domain = list(domain)
        return domain or []

    def filter_function(self, records, field_expr, operator, value):
        getter = self.expression_getter(field_expr)

        if (self.bypass_search_access or operator == 'any!') and not records.env.su:
            # When filtering with bypass access, search the corecords with sudo
            # and a special key in the context. To evaluate sub-domains, the
            # special key makes the environment un-sudoed before evaluation.
            expr_getter = getter
            sudo_env = records.sudo().with_context(filter_function_reset_sudo=True).env
            getter = lambda rec: expr_getter(rec.with_env(sudo_env))  # noqa: E731

        corecords = getter(records)
        if operator in ('any', 'any!'):
            assert isinstance(value, Domain)
            if operator == 'any' and records.env.context.get('filter_function_reset_sudo'):
                corecords = corecords.sudo(False)._filtered_access('read')
            corecords = corecords.filtered_domain(value)
        elif operator == 'in' and isinstance(value, COLLECTION_TYPES):
            value = set(value)
            if False in value:
                if not corecords:
                    # shortcut, we know none of records has a corecord
                    return lambda _: True
                if len(value) > 1:
                    value.discard(False)
                    filter_values = self.filter_function(records, field_expr, 'in', value)
                    return lambda rec: not getter(rec) or filter_values(rec)
                return lambda rec: not getter(rec)
            corecords = corecords.filtered_domain(Domain('id', 'in', value))
        else:
            corecords = corecords.filtered_domain(Domain('id', operator, value))

        if not corecords:
            return lambda _: False

        ids = set(corecords._ids)
        return lambda rec: any(id_ in ids for val in getter(rec) for id_ in val._ids)


class Many2one(_Relational):
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

    :param bool bypass_search_access: whether access rights are bypassed on the
        comodel (default: ``False``)

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

    ondelete: OnDelete | None = None    # what to do when value is deleted
    delegate: bool = False              # whether self implements delegation

    def __init__(self, comodel_name: str | Sentinel = SENTINEL, string: str | Sentinel = SENTINEL, **kwargs):
        super().__init__(comodel_name=comodel_name, string=string, **kwargs)

    def _setup_attrs__(self, model_class, name):
        super()._setup_attrs__(model_class, name)
        # determine self.delegate
        if name in model_class._inherits.values():
            self.delegate = True
            # self.delegate implies self.bypass_search_access
            self.bypass_search_access = True
        elif self.delegate:
            comodel_name = self.comodel_name or 'comodel_name'
            raise TypeError((
                f"The delegate field {self} must be declared in the model class e.g.\n"
                f"_inherits = {{{comodel_name!r}: {name!r}}}"
            ))

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
        return super().update_db(model, columns)

    def update_db_column(self, model, column):
        super().update_db_column(model, column)
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

    def _update_inverse(self, records, value):
        for record in records:
            self._update_cache(record, self.convert_to_cache(value, record, validate=False))

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
        cache_value = self.convert_to_cache(value, records)
        records = self._filter_not_equal(records, cache_value)
        if not records:
            return

        # remove records from the cache of one2many fields of old corecords
        self._remove_inverses(records, cache_value)

        # update the cache of self
        self._update_cache(records, cache_value, dirty=True)

        # update the cache of one2many fields of new corecord
        self._update_inverses(records, cache_value)

    def _remove_inverses(self, records: BaseModel, value):
        """ Remove `records` from the cached values of the inverse fields (o2m) of `self`. """
        inverse_fields = records.pool.field_inverses[self]
        if not inverse_fields:
            return

        record_ids = set(records._ids)
        # align(id) returns a NewId if records are new, a real id otherwise
        align = (lambda id_: id_) if all(record_ids) else (lambda id_: id_ and NewId(id_))
        field_cache = self._get_cache(records.env)
        corecords = records.env[self.comodel_name].browse(
            align(coid) for record_id in records._ids
            if (coid := field_cache.get(record_id)) is not None
        )

        for invf in inverse_fields:
            inv_cache = invf._get_cache(corecords.env)
            for corecord in corecords:
                ids0 = inv_cache.get(corecord.id)
                if ids0 is not None:
                    ids1 = tuple(id_ for id_ in ids0 if id_ not in record_ids)
                    invf._update_cache(corecord, ids1)

    def _update_inverses(self, records: BaseModel, value):
        """ Add `records` to the cached values of the inverse fields (o2m) of `self`. """
        if value is None:
            return
        corecord = self.convert_to_record(value, records)
        for invf in records.pool.field_inverses[self]:
            valid_records = records.filtered_domain(invf.get_comodel_domain(corecord))
            if not valid_records:
                continue
            ids0 = invf._get_cache(corecord.env).get(corecord.id)
            # if the value for the corecord is not in cache, but this is a new
            # record, assign it anyway, as you won't be able to fetch it from
            # database (see `test_sale_order`)
            if ids0 is not None or not corecord.id:
                ids1 = tuple(unique((ids0 or ()) + valid_records._ids))
                invf._update_cache(corecord, ids1)

    def to_sql(self, model: BaseModel, alias: str) -> SQL:
        sql_field = super().to_sql(model, alias)
        if self.company_dependent:
            comodel = model.env[self.comodel_name]
            sql_field = SQL(
                '''(SELECT %(cotable_alias)s.id
                    FROM %(cotable)s AS %(cotable_alias)s
                    WHERE %(cotable_alias)s.id = %(ref)s)''',
                cotable=SQL.identifier(comodel._table),
                cotable_alias=SQL.identifier(Query.make_alias(comodel._table, 'exists')),
                ref=sql_field,
            )
        return sql_field

    def condition_to_sql(self, field_expr: str, operator: str, value, model: BaseModel, alias: str, query: Query) -> SQL:
        if operator not in ('any', 'not any', 'any!', 'not any!') or field_expr != self.name:
            # for other operators than 'any', just generate condition based on column type
            return super().condition_to_sql(field_expr, operator, value, model, alias, query)

        comodel = model.env[self.comodel_name]
        sql_field = model._field_to_sql(alias, field_expr, query)
        can_be_null = self not in model.env.registry.not_null_fields
        bypass_access = operator in ('any!', 'not any!') or self.bypass_search_access
        positive = operator in ('any', 'any!')

        # Decide whether to use a LEFT JOIN
        left_join = bypass_access and isinstance(value, Domain)
        if left_join and not positive:
            # For 'not any!', we get a better query with a NOT IN when we have a
            # lot of positive conditions which have a better chance to use
            # indexes.
            #   `field NOT IN (SELECT ... WHERE z = y)` better than
            #   `LEFT JOIN ... ON field = id WHERE z <> y`
            # There are some exceptions: we filter on 'id'.
            left_join = sum(
                (-1 if cond.operator in Domain.NEGATIVE_OPERATORS else 1)
                for cond in value.iter_conditions()
            ) < 0 or any(
                cond.field_expr == 'id' and cond.operator not in Domain.NEGATIVE_OPERATORS
                for cond in value.iter_conditions()
            )

        if left_join:
            comodel, coalias = self.join(model, alias, query)
            if not positive:
                value = (~value).optimize_full(comodel)
            sql = value._to_sql(comodel, coalias, query)
            if self.company_dependent:
                sql = self._condition_to_sql_company(sql, field_expr, operator, value, model, alias, query)
            if can_be_null:
                if positive:
                    sql = SQL("(%s IS NOT NULL AND %s)", sql_field, sql)
                else:
                    sql = SQL("(%s IS NULL OR %s)", sql_field, sql)
            return sql

        if isinstance(value, Domain):
            value = comodel._search(value, active_test=False, bypass_access=bypass_access)
        if isinstance(value, Query):
            subselect = value.subselect()
        elif isinstance(value, SQL):
            subselect = SQL("(%s)", value)
        else:
            raise TypeError(f"condition_to_sql() 'any' operator accepts Domain, SQL or Query, got {value}")
        sql = SQL(
            "%s%s%s",
            sql_field,
            SQL(" IN ") if positive else SQL(" NOT IN "),
            subselect,
        )
        if can_be_null and not positive:
            sql = SQL("(%s IS NULL OR %s)", sql_field, sql)
        if self.company_dependent:
            sql = self._condition_to_sql_company(sql, field_expr, operator, value, model, alias, query)
        return sql

    def join(self, model: BaseModel, alias: str, query: Query) -> tuple[BaseModel, str]:
        """ Add a LEFT JOIN to ``query`` by following field ``self``,
        and return the joined table's corresponding model and alias.
        """
        comodel = model.env[self.comodel_name]
        coalias = query.make_alias(alias, self.name)
        query.add_join('LEFT JOIN', coalias, comodel._table, SQL(
            "%s = %s",
            model._field_to_sql(alias, self.name, query),
            SQL.identifier(coalias, 'id'),
        ))
        return (comodel, coalias)


class _RelationalMulti(_Relational):
    r"Abstract class for relational fields \*2many."
    write_sequence = 20

    # Important: the cache contains the ids of all the records in the relation,
    # including inactive records.  Inactive records are filtered out by
    # convert_to_record(), depending on the context.

    def _update_inverse(self, records, value):
        new_id = value.id
        assert not new_id, "Field._update_inverse can only be called with a new id"
        field_cache = self._get_cache(records.env)
        for record_id in records._ids:
            assert not record_id, "Field._update_inverse can only be called with new records"
            cache_value = field_cache.get(record_id, SENTINEL)
            if cache_value is SENTINEL:
                records.env.transaction.field_data_patches[self][record_id].append(new_id)
            else:
                field_cache[record_id] = tuple(unique(cache_value + (new_id,)))

    def _update_cache(self, records, cache_value, dirty=False):
        field_patches = records.env.transaction.field_data_patches.get(self)
        if field_patches and records:
            for record in records:
                ids = field_patches.pop(record.id, ())
                if ids:
                    value = tuple(unique(itertools.chain(cache_value, ids)))
                else:
                    value = cache_value
                super()._update_cache(record, value, dirty)
            return
        super()._update_cache(records, cache_value, dirty)

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
        if not self.compute and isinstance(domain := self.domain, (list, Domain)):
            domain = Domain(domain)
            depends = unique(itertools.chain(depends, (
                self.name + '.' + condition.field_expr
                for condition in domain.iter_conditions()
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

    def write_batch(self, records_commands_list: Sequence[tuple[BaseModel, typing.Any]], create: bool = False) -> None:
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

    def write_real(self, records_commands_list: Sequence[tuple[BaseModel, list[CommandValue]]], create: bool = False) -> None:
        raise NotImplementedError

    def write_new(self, records_commands_list: Sequence[tuple[BaseModel, list[CommandValue]]]) -> None:
        raise NotImplementedError

    def _check_sudo_commands(self, comodel):
        # if the model doesn't accept sudo commands
        if not comodel._allow_sudo_commands:
            # Then, disable sudo and reset the transaction origin user
            return comodel.sudo(False).with_user(comodel.env.transaction.default_env.uid)
        return comodel

    def condition_to_sql(self, field_expr: str, operator: str, value, model: BaseModel, alias: str, query: Query) -> SQL:
        assert field_expr == self.name, "Supporting condition only to field"
        comodel = model.env[self.comodel_name]
        if not self.store:
            raise ValueError(f"Cannot convert {self} to SQL because it is not stored")

        # update the operator to 'any'
        if operator in ('in', 'not in'):
            operator = 'any' if operator == 'in' else 'not any'
        assert operator in ('any', 'not any', 'any!', 'not any!'), \
            f"Relational field {self} expects 'any' operator"
        exists = operator in ('any', 'any!')

        # check the value and execute the query
        if isinstance(value, COLLECTION_TYPES):
            value = OrderedSet(value)
            comodel = comodel.sudo().with_context(active_test=False)
            if False in value:
                #  [not]in (False, 1) => split conditions
                #  We want records that have a record such as condition or
                #  that don't have any records.
                if len(value) > 1:
                    in_operator = 'in' if exists else 'not in'
                    return SQL(
                        "(%s OR %s)" if exists else "(%s AND %s)",
                        self.condition_to_sql(field_expr, in_operator, (False,), model, alias, query),
                        self.condition_to_sql(field_expr, in_operator, value - {False}, model, alias, query),
                    )
                #  in (False) => not any (Domain.TRUE)
                #  not in (False) => any (Domain.TRUE)
                value = comodel._search(Domain.TRUE)
                exists = not exists
            else:
                value = comodel.browse(value)._as_query(ordered=False)
        elif isinstance(value, SQL):
            # wrap SQL into a simple query
            comodel = comodel.sudo()
            value = Domain('id', 'any', value)
        coquery = self._get_query_for_condition_value(model, comodel, operator, value)
        return self._condition_to_sql_relational(model, alias, exists, coquery, query)

    def _get_query_for_condition_value(self, model: BaseModel, comodel: BaseModel, operator: str, value: Domain | Query) -> Query:
        """ Return Query run on the comodel with the field.domain injected."""
        field_domain = self.get_comodel_domain(model)
        if isinstance(value, Domain):
            domain = value & field_domain
            comodel = comodel.with_context(**self.context)
            bypass_access = self.bypass_search_access or operator in ('any!', 'not any!')
            query = comodel._search(domain, bypass_access=bypass_access)
            assert isinstance(query, Query)
            return query
        if isinstance(value, Query):
            # add the field_domain to the query
            domain = field_domain.optimize_full(comodel)
            if not domain.is_true():
                # TODO should clone/copy Query value
                value.add_where(domain._to_sql(comodel, value.table, value))
            return value
        raise NotImplementedError(f"Cannot build query for {value}")

    def _condition_to_sql_relational(self, model: BaseModel, alias: str, exists: bool, coquery: Query, query: Query) -> SQL:
        raise NotImplementedError


class One2many(_RelationalMulti):
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

    :param bool bypass_search_access: whether access rights are bypassed on the
        comodel (default: ``False``)

    The attributes ``comodel_name`` and ``inverse_name`` are mandatory except in
    the case of related fields or field extensions.
    """
    type = 'one2many'

    inverse_name: str | None = None     # name of the inverse field
    copy: bool = False                  # o2m are not copied by default

    def __init__(self, comodel_name: str | Sentinel = SENTINEL, inverse_name: str | Sentinel = SENTINEL,
                 string: str | Sentinel = SENTINEL, **kwargs):
        super().__init__(
            comodel_name=comodel_name,
            inverse_name=inverse_name,
            string=string,
            **kwargs
        )

    def setup_nonrelated(self, model):
        super().setup_nonrelated(model)
        if self.inverse_name:
            # link self to its inverse field and vice-versa
            comodel = model.env[self.comodel_name]
            try:
                comodel._fields[self.inverse_name]
            except KeyError:
                raise ValueError(f"{self.inverse_name!r} declared in {self!r} does not exist on {comodel._name!r}.")

    def setup_inverses(self, registry, inverses):
        if self.inverse_name:
            # link self to its inverse field and vice-versa
            invf = registry[self.comodel_name]._fields[self.inverse_name]
            if isinstance(invf, (Many2one, Many2oneReference)):
                # setting one2many fields only invalidates many2one inverses;
                # integer inverses (res_model/res_id pairs) are not supported
                inverses.add(self, invf)
            inverses.add(invf, self)

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

    def _additional_domain(self, env) -> Domain:
        if self.comodel_name and self.inverse_name:
            comodel = env.registry[self.comodel_name]
            inverse_field = comodel._fields[self.inverse_name]
            if inverse_field.type == 'many2one_reference':
                return Domain(inverse_field.model_field, '=', self.model_name)
        return Domain.TRUE

    def get_comodel_domain(self, model: BaseModel) -> Domain:
        return super().get_comodel_domain(model) & self._additional_domain(model.env)

    def _internal_description_domain_raw(self, env) -> str | list:
        domain = super()._internal_description_domain_raw(env)
        additional_domain = self._additional_domain(env)
        if additional_domain.is_true():
            return domain
        return f"({domain}) + ({additional_domain})"

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
        domain = self.get_comodel_domain(records) & Domain(inverse, 'in', records.ids)
        field_names = [inverse]
        if comodel._active_name:
            field_names.append(comodel._active_name)
        try:
            lines = comodel.search_fetch(domain, field_names)
        except AccessError as e:
            raise AccessError(records.env._("Failed to read field %s", self) + '\n' + str(e)) from e

        # group lines by inverse field (without prefetching other fields)
        get_id = (lambda rec: rec.id) if inverse_field.type == 'many2one' else int
        group = defaultdict(list)
        for line in lines:
            # line[inverse] may be a record or an integer
            group[get_id(line[inverse])].append(line.id)

        # store result in cache
        values = [tuple(group[id_]) for id_ in records._ids]
        self._insert_cache(records, values)

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
                        domain = self.get_comodel_domain(model) & Domain(inverse, 'in', recs.ids) & Domain('id', 'not in', lines.ids)
                        unlink(comodel.search(domain))
                        lines[inverse] = recs[-1]

            flush()

        else:
            ids = OrderedSet(rid for recs, cs in records_commands_list for rid in recs._ids)
            records = records_commands_list[0][0].browse(ids)

            def link(record, lines):
                ids = record[self.name]._ids
                self._update_cache(record, tuple(unique(ids + lines._ids)))

            def unlink(lines):
                for record in records:
                    self._update_cache(record, (record[self.name] - lines)._ids)

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
                        self._update_cache(recs, ())
                        lines = comodel.browse(command[2] if command[0] == Command.SET else [])
                        self._update_cache(recs[-1], lines._ids)

    def write_new(self, records_commands_list):
        if not records_commands_list:
            return

        model = records_commands_list[0][0].browse()
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
                inverse_field._update_cache(record[self.name], record.id)

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
                        self._update_cache(recs, ())
                    elif command[0] == Command.SET:
                        # assign the given lines to the last record only
                        self._update_cache(recs, ())
                        last, lines = recs[-1], browse(command[2])
                        self._update_cache(last, lines._ids)
                        inverse_field._update_cache(lines, last.id)

        else:
            def link(record, lines):
                ids = record[self.name]._ids
                self._update_cache(record, tuple(unique(ids + lines._ids)))

            def unlink(lines):
                for record in records:
                    self._update_cache(record, (record[self.name] - lines)._ids)

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
                        self._update_cache(recs, ())
                        lines = browse(command[2] if command[0] == Command.SET else [])
                        self._update_cache(recs[-1], lines._ids)

    def _get_query_for_condition_value(self, model: BaseModel, comodel: BaseModel, operator, value) -> Query:
        inverse_field = comodel._fields[self.inverse_name]
        if inverse_field not in comodel.env.registry.not_null_fields:
            # In the condition, one must avoid subqueries to return
            # NULL values, since it makes the IN test NULL instead
            # of FALSE.  This may discard expected results, as for
            # instance "id NOT IN (42, NULL)" is never TRUE.
            if isinstance(value, Domain):
                value &= Domain(inverse_field.name, 'not in', {False})
            else:
                coquery = super()._get_query_for_condition_value(model, comodel, operator, value)
                coquery.add_where(SQL(
                    "%s IS NOT NULL",
                    comodel._field_to_sql(coquery.table, inverse_field.name, coquery),
                ))
                return coquery
        return super()._get_query_for_condition_value(model, comodel, operator, value)

    def _condition_to_sql_relational(self, model: BaseModel, alias: str, exists: bool, coquery: Query, query: Query) -> SQL:
        if coquery.is_empty():
            return Domain(not exists)._to_sql(model, alias, query)

        comodel = model.env[self.comodel_name].sudo()
        inverse_field = comodel._fields[self.inverse_name]
        if not inverse_field.store:
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

        subselect = coquery.subselect(
            SQL("%s AS __inverse", comodel._field_to_sql(coquery.table, inverse_field.name, coquery))
        )
        return SQL(
            "%sEXISTS(SELECT FROM %s AS __sub WHERE __inverse = %s)",
            SQL() if exists else SQL("NOT "),
            subselect,
            SQL.identifier(alias, 'id'),
        )


class Many2many(_RelationalMulti):
    """ Many2many field; the value of such a field is the recordset.

    :param str comodel_name: name of the target model (string)
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

    _explicit: bool = True              # whether schema is explicitly given
    relation: str | None = None         # name of table
    column1: str | None = None          # column of table referring to model
    column2: str | None = None          # column of table referring to comodel
    ondelete: OnDelete | None = 'cascade'  # optional ondelete for the column2 fkey

    def __init__(self, comodel_name: str | Sentinel = SENTINEL, relation: str | Sentinel = SENTINEL,
                 column1: str | Sentinel = SENTINEL, column2: str | Sentinel = SENTINEL,
                 string: str | Sentinel = SENTINEL, **kwargs):
        super().__init__(
            comodel_name=comodel_name,
            relation=relation,
            column1=column1,
            column2=column2,
            string=string,
            **kwargs
        )

    def setup_nonrelated(self, model: BaseModel) -> None:
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
            # check whether other fields use the same schema
            fields = model.pool.many2many_relations[self.relation, self.column1, self.column2]
            for mname, fname in fields:
                field = model.pool[mname]._fields[fname]
                if (
                    field is self
                ) or (    # same model: relation parameters must be explicit
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
            fields.add((self.model_name, self.name))

    def setup_inverses(self, registry, inverses):
        if self.relation:
            # retrieve inverse fields, and link them in field_inverses
            for mname, fname in registry.many2many_relations[self.relation, self.column2, self.column1]:
                field = registry[mname]._fields[fname]
                inverses.add(self, field)
                inverses.add(field, self)

    def update_db(self, model, columns):
        cr = model.env.cr
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

        # bypass the access during search if method is overwriten to avoid
        # possibly filtering all records of the comodel before joining
        filter_access = self.bypass_search_access and type(comodel)._search is not BaseModel._search

        # make the query for the lines
        domain = self.get_comodel_domain(records)
        try:
            query = comodel._search(domain, order=comodel._order, bypass_access=filter_access)
        except AccessError as e:
            raise AccessError(records.env._("Failed to read field %s", self) + '\n' + str(e)) from e

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

        # filter using record rules
        if filter_access and group:
            corecord_ids = OrderedSet(id_ for ids in group.values() for id_ in ids)
            accessible_corecords = comodel.browse(corecord_ids)._filtered_access('read')
            if len(accessible_corecords) < len(corecord_ids):
                # some records are inaccessible, remove them from groups
                corecord_ids = set(accessible_corecords._ids)
                for id1, ids in group.items():
                    group[id1] = [id_ for id_ in ids if id_ in corecord_ids]

        # store result in cache
        values = [tuple(group[id_]) for id_ in records._ids]
        self._insert_cache(records, values)

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
            missing_ids = tuple(self._cache_missing_ids(records))
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

        # check comodel access of added records
        # we check the su flag of the environment of records, because su may be
        # disabled on the comodel
        if not model.env.su:
            try:
                comodel.browse(
                    co_id
                    for rec_id, new_co_ids in new_relation.items()
                    for co_id in new_co_ids - old_relation[rec_id]
                ).check_access('read')
            except AccessError as e:
                raise AccessError(model.env._("Failed to write field %s", self) + "\n" + str(e))

        # update the cache of self
        for record in records:
            self._update_cache(record, tuple(new_relation[record.id]))

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
                domain = invf.get_comodel_domain(comodel)
                valid_ids = set(records.filtered_domain(domain)._ids)
                if not valid_ids:
                    continue
                inv_cache = invf._get_cache(comodel.env)
                for y, xs in y_to_xs.items():
                    corecord = comodel.browse(y)
                    try:
                        ids0 = inv_cache[corecord.id]
                        ids1 = tuple(set(ids0) | (xs & valid_ids))
                        invf._update_cache(corecord, ids1)
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
                inv_cache = invf._get_cache(comodel.env)
                for y, xs in y_to_xs.items():
                    corecord = comodel.browse(y)
                    try:
                        ids0 = inv_cache[corecord.id]
                        ids1 = tuple(id_ for id_ in ids0 if id_ not in xs)
                        invf._update_cache(corecord, ids1)
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
        for record in records:
            self._update_cache(record, tuple(new_relation[record.id]))

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
                domain = invf.get_comodel_domain(comodel)
                valid_ids = set(records.filtered_domain(domain)._ids)
                if not valid_ids:
                    continue
                inv_cache = invf._get_cache(comodel.env)
                for y, xs in y_to_xs.items():
                    corecord = comodel.browse((y,))
                    try:
                        ids0 = inv_cache[corecord.id]
                        ids1 = tuple(set(ids0) | (xs & valid_ids))
                        invf._update_cache(corecord, ids1)
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
                inv_cache = invf._get_cache(comodel.env)
                for y, xs in y_to_xs.items():
                    corecord = comodel.browse((y,))
                    try:
                        ids0 = inv_cache[corecord.id]
                        ids1 = tuple(id_ for id_ in ids0 if id_ not in xs)
                        invf._update_cache(corecord, ids1)
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
        if coquery.is_empty():
            return SQL("FALSE") if exists else SQL("TRUE")
        rel_table, rel_id1, rel_id2 = self.relation, self.column1, self.column2
        rel_alias = query.make_alias(alias, self.name)
        if not coquery.where_clause:
            # case: no constraints on table and we have foreign keys
            # so we can inverse the operator and check existence
            exists = not exists
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


class PrefetchMany2one(Reversible):
    """ Iterable for the values of a many2one field on the prefetch set of a given record. """
    __slots__ = ('field', 'record')

    def __init__(self, record: BaseModel, field: Many2one):
        self.record = record
        self.field = field

    def __iter__(self):
        field_cache = self.field._get_cache(self.record.env)
        return unique(
            coid for id_ in self.record._prefetch_ids
            if (coid := field_cache.get(id_)) is not None
        )

    def __reversed__(self):
        field_cache = self.field._get_cache(self.record.env)
        return unique(
            coid for id_ in reversed(self.record._prefetch_ids)
            if (coid := field_cache.get(id_)) is not None
        )


class PrefetchX2many(Reversible):
    """ Iterable for the values of an x2many field on the prefetch set of a given record. """
    __slots__ = ('field', 'record')

    def __init__(self, record: BaseModel, field: _RelationalMulti):
        self.record = record
        self.field = field

    def __iter__(self):
        field_cache = self.field._get_cache(self.record.env)
        return unique(
            coid
            for id_ in self.record._prefetch_ids
            for coid in field_cache.get(id_, ())
        )

    def __reversed__(self):
        field_cache = self.field._get_cache(self.record.env)
        return unique(
            coid
            for id_ in reversed(self.record._prefetch_ids)
            for coid in field_cache.get(id_, ())
        )
