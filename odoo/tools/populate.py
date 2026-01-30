"""
Database Population via Duplication

This tool provides utilities to duplicate records across models in Odoo, while maintaining referential integrity,
handling field variations, and optimizing insertion performance. The duplication is controlled by a `factors` argument
that specifies how many times each record should be duplicated. The duplication process takes into account fields
that require unique constraints, distributed values (e.g., date fields), and relational fields (e.g., Many2one, Many2many).

Key Features:
-------------
1. **Field Variations**: Handles variations for certain fields to ensure uniqueness or to distribute values, such as:
   - Char/Text fields: Appends a postfix or variation to existing data.
   - Date/Datetime fields: Distributes dates within a specified range.

2. **Efficient Duplication**: Optimizes the duplication process by:
   - Dropping and restoring indexes to speed up bulk inserts.
   - Disabling foreign key constraint checks during duplication to avoid integrity errors.
   - Dynamically adjusting sequences to maintain consistency in auto-increment fields like `id`.

3. **Field-Specific Logic**:
   - Unique fields are identified and modified to avoid constraint violations.
   - Many2one fields are remapped to newly duplicated records.
   - One2many and Many2many relationships are handled by duplicating both sides of the relationship.

4. **Foreign Key and Index Management**:
   - Indexes are temporarily dropped during record creation and restored afterward to improve performance.
   - Foreign key checks are disabled temporarily to prevent constraint violations during record insertion.

5. **Dependency Management**: Ensures proper population order of models with dependencies (e.g., `_inherits` fields)
   by resolving dependencies before duplicating records.

6. **Dynamic SQL Generation**: Uses SQL queries to manipulate and duplicate data directly at the database level,
   ensuring performance and flexibility in handling large datasets.
"""

from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime

from psycopg2.errors import InsufficientPrivilege
from dateutil.relativedelta import relativedelta
import logging

from odoo.api import Environment
from odoo.tools.sql import SQL
from odoo.fields import Field, Many2one
from odoo.models import Model


_logger = logging.getLogger(__name__)

# Min/Max value for a date/datetime field
MIN_DATETIME = datetime((datetime.now() - relativedelta(years=4)).year, 1, 1)
MAX_DATETIME = datetime.now()


def get_field_variation_date(model: Model, field: Field, factor: int, series_alias: str) -> SQL:
    """
    Distribute the duplication series evenly between [field-total_days, field].
    We use a hard limit of (MAX_DATETIME - MIN_DATETIME) years in the past to avoid
    setting duplicated records too far back in the past.
    """
    total_days = min((MAX_DATETIME - MIN_DATETIME).days, factor)
    cast_type = SQL(field._column_type[1])

    def redistribute(value):
        return SQL(
            "(%(value)s - (%(factor)s - %(series_alias)s) * (%(total_days)s::float/%(factor)s) * interval '1 days')::%(cast_type)s",
            value=value,
            factor=factor,
            series_alias=SQL.identifier(series_alias),
            total_days=total_days,
            cast_type=cast_type,
        )

    if not field.company_dependent:
        return redistribute(SQL.identifier(field.name))
    # company_dependent -> jsonb
    return SQL(
        '(SELECT jsonb_object_agg(key, %(expr)s) FROM jsonb_each_text(%(field)s))',
        expr=redistribute(SQL('value::%s', cast_type)),
        field=SQL.identifier(field.name),
    )


def get_field_variation_char(field: Field, postfix: str | SQL | None = None) -> SQL:
    """
    Append the `postfix` string to a char|text field.
    If no postfix is provided, returns no variation
    """
    if postfix is None:
        return SQL.identifier(field.name)
    if not isinstance(postfix, SQL):
        postfix = SQL.identifier(postfix)
    # if the field is translatable, it's a JSONB column, we vary all values for each key
    if field.translate:
        return SQL("""(
            SELECT jsonb_object_agg(key, value || %(postfix)s)
            FROM jsonb_each_text(%(field)s)
        )""", field=SQL.identifier(field.name), postfix=postfix)
    else:
        # no postfix for fields that are an '' (no point to)
        # or '/' (default/draft name for many model's records)
        return SQL("""
            CASE
                WHEN %(field)s IS NULL OR %(field)s IN ('/', '')
                THEN %(field)s
                ELSE %(field)s || %(postfix)s
            END
        """, field=SQL.identifier(field.name), postfix=postfix)


class PopulateContext:
    def __init__(self):
        self.has_session_replication_role = True

    @contextmanager
    def ignore_indexes(self, model: Model):
        """
        Temporarily drop indexes on table to speed up insertion.
        PKey and Unique indexes are kept for constraints
        """
        indexes = model.env.execute_query_dict(SQL("""
            SELECT indexname AS name, indexdef AS definition
              FROM pg_indexes
             WHERE tablename = %s
               AND schemaname = current_schema
               AND indexname NOT LIKE %s
               AND indexdef NOT LIKE %s
        """, model._table, '%pkey', '%UNIQUE%'))
        if indexes:
            _logger.info('Dropping indexes on table %s...', model._table)
            for index in indexes:
                model.env.cr.execute(SQL('DROP INDEX %s CASCADE', SQL.identifier(index['name'])))
            yield
            _logger.info('Adding indexes back on table %s...', model._table)
            for index in indexes:
                model.env.cr.execute(index['definition'])
        else:
            yield

    @contextmanager
    def ignore_fkey_constraints(self, model: Model):
        """
        Disable Fkey constraints checks by setting the session to replica.
        """
        if self.has_session_replication_role:
            try:
                model.env.cr.execute('SET session_replication_role TO replica')
                yield
                model.env.cr.execute('RESET session_replication_role')
            except InsufficientPrivilege:
                _logger.warning("Cannot ignore Fkey constraints during insertion due to insufficient privileges for current pg_role. "
                                "Resetting transaction and retrying to populate without dropping the check on Fkey constraints. "
                                "The bulk insertion will be vastly slower than anticipated.")
                model.env.cr.rollback()
                self.has_session_replication_role = False
                yield
        else:
            yield


def field_needs_variation(model: Model, field: Field) -> bool:
    """
    Return True/False depending on if the field needs to be varied.
    Might be necessary in the case of:
    - unique constraints
    - varying dates for better distribution
    - field will be part of _rec_name_search, therefor variety is needed for effective searches
    - field has a trigram index on it
    """
    def is_unique(model_, field_):
        """
        An unique constraint is enforced by Postgres as an unique index,
        whether it's defined as a constraint on the table, or as an manual unique index.
        Both type of constraint are present in the index catalog
        """
        query = SQL("""
        SELECT EXISTS(SELECT 1
              FROM pg_index idx
                   JOIN pg_class t ON t.oid = idx.indrelid
                   JOIN pg_class i ON i.oid = idx.indexrelid
                   JOIN pg_attribute a ON a.attnum = ANY (idx.indkey) AND a.attrelid = t.oid
              WHERE t.relname = %s  -- tablename
                AND a.attname = %s  -- column
                AND t.relnamespace = current_schema::regnamespace
                AND idx.indisunique = TRUE) AS is_unique;
        """, model_._table, field_.name)
        return model_.env.execute_query(query)[0][0]

    # Many2one fields are not considered, as a name_search would resolve it to the _rec_names_search of the related model
    in_names_search = model._rec_names_search and field.name in model._rec_names_search
    in_name = model._rec_name and field.name == model._rec_name
    if (in_name or in_names_search) and field.type != 'many2one':
        return True
    if field.type in ('date', 'datetime'):
        return True
    if field.index == 'trigram':
        return True
    return is_unique(model, field)


def get_field_variation(model: Model, field: Field, factor: int, series_alias: str) -> SQL:
    """
    Returns a variation of the source field,
    to avoid unique constraint, or better distribute data.

    :return: a SQL(identifier|expression|subquery)
    """
    match field.type:
        case 'char' | 'text':
            return get_field_variation_char(field, postfix=series_alias)
        case 'date' | 'datetime':
            return get_field_variation_date(model, field, factor, series_alias)
        case 'html':
            # For the sake of simplicity we don't vary html fields
            return SQL.identifier(field.name)
        case _:
            _logger.warning("The field %s of type %s was marked to be varied, "
                            "but no variation branch was found! Defaulting to a raw copy.", field, field.type)
            # fallback on a raw copy
            return SQL.identifier(field.name)


def fetch_last_id(model: Model) -> int:
    query = SQL('SELECT id FROM %s ORDER BY id DESC LIMIT 1', SQL.identifier(model._table))
    return model.env.execute_query(query)[0][0]


def populate_field(model: Model, field: Field, populated: dict[Model, int], factors: dict[Model, int],
                   table_alias: str = 't', series_alias: str = 's') -> SQL | None:
    """
    Returns the source expression for copying the field (SQL(identifier|expression|subquery) | None)
    `table_alias` and `series_alias` are the identifiers used to reference
    the currently being populated table and it's series, respectively.
    """
    def copy_noop():
        return None

    def copy_raw(field_):
        return SQL.identifier(field_.name)

    def copy(field_):
        if field_needs_variation(model, field_):
            return get_field_variation(model, field_, factors[model], series_alias)
        else:
            return copy_raw(field_)

    def copy_id():
        last_id = fetch_last_id(model)
        populated[model] = last_id  # this adds the model in the populated dict
        return SQL('id + %(last_id)s * %(series_alias)s', last_id=last_id, series_alias=SQL.identifier(series_alias))

    def copy_many2one(field_):
        # if the comodel was priorly populated, remap the many2one to the new copies
        if (comodel := model.env[field_.comodel_name]) in populated:
            comodel_max_id = populated[comodel]
            # we use MOD() instead of %, because % cannot be correctly escaped, it's a limitation of the SQL wrapper
            return SQL("%(table_alias)s.%(field_name)s + %(comodel_max_id)s * (MOD(%(series_alias)s - 1, %(factor)s) + 1)",
                        table_alias=SQL.identifier(table_alias),
                        field_name=SQL.identifier(field_.name),
                        comodel_max_id=comodel_max_id,
                        series_alias=SQL.identifier(series_alias),
                        factor=factors[comodel])
        return copy(field_)

    if field.name == 'id':
        return copy_id()
    match field.type:
        case 'one2many':
            # there is nothing to copy, as it's value is implicitly read from the inverse Many2one
            return copy_noop()
        case 'many2many':
            # there is nothing to do, the copying of the m2m will be handled when copying the relation table
            return copy_noop()
        case 'many2one':
            return copy_many2one(field)
        case 'many2one_reference':
            # TODO: in the case of a reference field, there is no comodel,
            #  but it's specified as the value of the field specified by model_field.
            #  Not really sure how to handle this, as it involves reading the content pointed by model_field
            #  to check on-the-fly if it's populated or not python-side, so for now we raw-copy it.
            #  If we need to read on-the-fly, the populated structure needs to be in DB (via a new Model?)
            return copy(field)
        case 'binary':
            # copy only binary field that are inlined in the table
            return copy(field) if not field.attachment else copy_noop()
        case _:
            return copy(field)


def populate_model(model: Model, populated: dict[Model, int], factors: dict[Model, int], separator_code: str) -> None:

    def update_sequence(model_):
        model_.env.execute_query(SQL("SELECT SETVAL(%(sequence)s, %(last_id)s, TRUE)",
                              sequence=f"{model_._table}_id_seq", last_id=fetch_last_id(model_)))

    def has_column(field_):
        return field_.store and field_.column_type

    assert model not in populated, f"We do not populate a model ({model}) that has already been populated."
    _logger.info('Populating model %s %s times...', model._name, factors[model])
    dest_fields = []
    src_fields = []
    update_fields = []
    table_alias = 't'
    series_alias = 's'
    # process all stored fields (that has a respective column), if the model has an 'id', it's processed first
    for _, field in sorted(model._fields.items(), key=lambda pair: pair[0] != 'id'):
        if has_column(field):
            if field_needs_variation(model, field) and field.type in ('char', 'text'):
                update_fields.append(field)
            if src := populate_field(model, field, populated, factors, table_alias, series_alias):
                dest_fields.append(SQL.identifier(field.name))
                src_fields.append(src)
    # Update char/text fields for existing rows, to allow re-entrance
    if update_fields:
        query = SQL('UPDATE %(table)s SET (%(src_columns)s) = ROW(%(dest_columns)s)',
                    table=SQL.identifier(model._table),
                    src_columns=SQL(', ').join(SQL.identifier(field.name) for field in update_fields),
                    dest_columns=SQL(', ').join(
                        get_field_variation_char(field, postfix=SQL('CHR(%s)', separator_code))
                        for field in update_fields))
        model.env.cr.execute(query)
    query = SQL("""
        INSERT INTO %(table)s (%(dest_columns)s)
        SELECT %(src_columns)s FROM %(table)s %(table_alias)s,
        GENERATE_SERIES(1, %(factor)s) %(series_alias)s
    """, table=SQL.identifier(model._table), factor=factors[model],
         dest_columns=SQL(', ').join(dest_fields), src_columns=SQL(', ').join(src_fields),
         table_alias=SQL.identifier(table_alias), series_alias=SQL.identifier(series_alias))
    model.env.cr.execute(query)
    # normally copying the 'id' will set the model entry in the populated dict,
    # but for the case of a table with no 'id' (ex: Many2many), we add manually,
    # by reading the key and having the defaultdict do the insertion, with a default value of 0
    if populated[model]:
        # in case we populated a model with an 'id', we update the sequence
        update_sequence(model)


class Many2oneFieldWrapper(Many2one):
    def __init__(self, model, field_name, comodel_name):
        super().__init__(comodel_name)
        self._setup_attrs__(model, field_name)  # setup most of the default attrs


class Many2manyModelWrapper:
    def __init__(self, env, field):
        self._name = field.relation  # a m2m doesn't have a _name, so we use the tablename
        self._table = field.relation
        self._inherits = {}
        self.env = env
        self._rec_name = None
        self._rec_names_search = []
        # if the field is inherited, the column attributes are defined on the base_field
        column1 = field.column1 or field.base_field.column1
        column2 = field.column2 or field.base_field.column2
        # column1 refers to the model, while column2 refers to the comodel
        self._fields = {
            field.column1: Many2oneFieldWrapper(self, column1, field.model_name),
            field.column2: Many2oneFieldWrapper(self, column2, field.comodel_name),
        }

    def __repr__(self):
        return f"<Many2manyModelWrapper({self._name!r})>"

    def __eq__(self, other):
        return self._name == other._name

    def __hash__(self):
        return hash(self._name)


def infer_many2many_model(env: Environment, field: Field) -> Model | Many2manyModelWrapper:
    """
    Returns the relation model used for the m2m:
    - If it's a custom model, return the model
    - If it's an implicite table generated by the ORM,
      return a wrapped model that behaves like a fake duck-typed model for the population algorithm
    """
    # check if the relation is an existing model
    for model_name, model_class in env.registry.items():
        if model_class._table == field.relation:
            return env[model_name]
    # the relation is a relational table, return a wrapped version
    return Many2manyModelWrapper(env, field)


def populate_models(model_factors: dict[Model, int], separator_code: int) -> None:
    """
    Create factors new records using existing records as templates.

    If a dependency is found for a specific model, but it isn't specified by the user,
    it will inherit the factor of the dependant model.
    """

    def has_records(model_):
        query = SQL('SELECT EXISTS (SELECT 1 FROM %s)', SQL.identifier(model_._table))
        return model_.env.execute_query(query)[0][0]

    populated: dict[Model, int] = defaultdict(int)
    ctx: PopulateContext = PopulateContext()

    def process(model_):
        if model_ in populated:
            return
        if not has_records(model_):  # if there are no records, there is nothing to populate
            populated[model_] = 0
            return

        # if the model has _inherits, the delegated models need to have been populated before the current one
        for model_name in model_._inherits:
            process(model_.env[model_name])

        with ctx.ignore_fkey_constraints(model_), ctx.ignore_indexes(model_):
            populate_model(model_, populated, model_factors, separator_code)

        # models on the other end of X2many relation should also be populated (ex: to avoid SO with no SOL)
        for field in model_._fields.values():
            if field.store and field.copy:
                match field.type:
                    case 'one2many':
                        comodel = model_.env[field.comodel_name]
                        if comodel != model_:
                            model_factors[comodel] = model_factors[model_]
                            process(comodel)
                    case 'many2many':
                        m2m_model = infer_many2many_model(model_.env, field)
                        model_factors[m2m_model] = model_factors[model_]
                        process(m2m_model)

    for model in list(model_factors):
        process(model)
