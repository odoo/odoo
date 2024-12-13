from __future__ import annotations

import ast
import contextlib
import copy
import json
import typing
import uuid
from collections import defaultdict
from operator import attrgetter

from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.tools import SQL, OrderedSet, is_list_of
from odoo.tools.misc import has_list_types
from odoo.tools.translate import _

from .domains import Domain
from .fields import Field, _logger
from .models import BaseModel
from .utils import COLLECTION_TYPES, SQL_OPERATORS, parse_field_expr, regex_alphanumeric

if typing.TYPE_CHECKING:
    from odoo.tools import Query

NoneType = type(None)


def check_property_field_value_name(property_name):
    if not (0 < len(property_name) <= 512) or not regex_alphanumeric.match(property_name):
        raise ValueError(f"Wrong property field value name {property_name!r}.")


class Properties(Field):
    """ Field that contains a list of properties (aka "sub-field") based on
    a definition defined on a container. Properties are pseudo-fields, acting
    like Odoo fields but without being independently stored in database.

    This field allows a light customization based on a container record. Used
    for relationships such as <project.project> / <project.task>,... New
    properties can be created on the fly without changing the structure of the
    database.

    The "definition_record" define the field used to find the container of the
    current record. The container must have a :class:`~odoo.fields.PropertiesDefinition`
    field "definition_record_field" that contains the properties definition
    (type of each property, default value)...

    Only the value of each property is stored on the child. When we read the
    properties field, we read the definition on the container and merge it with
    the value of the child. That way the web client has access to the full
    field definition (property type, ...).
    """
    type = 'properties'
    _column_type = ('jsonb', 'jsonb')
    copy = False
    prefetch = False
    write_sequence = 10              # because it must be written after the definition field

    # the field is computed editable by design (see the compute method below)
    store = True
    readonly = False
    precompute = True

    definition = None
    definition_record = None         # field on the current model that point to the definition record
    definition_record_field = None   # field on the definition record which defined the Properties field definition

    _description_definition_record = property(attrgetter('definition_record'))
    _description_definition_record_field = property(attrgetter('definition_record_field'))

    ALLOWED_TYPES = (
        # standard types
        'boolean', 'integer', 'float', 'char', 'date', 'datetime',
        # relational like types
        'many2one', 'many2many', 'selection', 'tags',
        # UI types
         'separator',
    )

    def _setup_attrs(self, model_class, name):
        super()._setup_attrs(model_class, name)
        self._setup_definition_attrs()

    def _setup_definition_attrs(self):
        if self.definition:
            # determine definition_record and definition_record_field
            assert self.definition.count(".") == 1
            self.definition_record, self.definition_record_field = self.definition.rsplit('.', 1)

            # make the field computed, and set its dependencies
            self._depends = (self.definition_record, )
            self.compute = self._compute

    def setup_related(self, model):
        super().setup_related(model)
        if self.inherited_field and not self.definition:
            self.definition = self.inherited_field.definition
            self._setup_definition_attrs()

    # Database/cache format: a value is either None, or a dict mapping property
    # names to their corresponding value, like
    #
    #       {
    #           '3adf37f3258cfe40': 'red',
    #           'aa34746a6851ee4e': 1337,
    #       }
    #
    def convert_to_column(self, value, record, values=None, validate=True):
        if not value:
            return None

        value = self.convert_to_cache(value, record, validate=validate)
        return json.dumps(value)

    def convert_to_cache(self, value, record, validate=True):
        # any format -> cache format {name: value} or None
        if not value:
            return None

        if isinstance(value, dict):
            # avoid accidental side effects from shared mutable data
            return copy.deepcopy(value)

        if isinstance(value, str):
            value = json.loads(value)
            if not isinstance(value, dict):
                raise ValueError(f"Wrong property value {value!r}")
            return value

        if isinstance(value, list):
            # Convert the list with all definitions into a simple dict
            # {name: value} to store the strict minimum on the child
            self._remove_display_name(value)
            return self._list_to_dict(value)

        raise ValueError(f"Wrong property type {type(value)!r}")

    # Record format: the value is either False, or a dict mapping property
    # names to their corresponding value, like
    #
    #       {
    #           '3adf37f3258cfe40': 'red',
    #           'aa34746a6851ee4e': 1337,
    #       }
    #
    def convert_to_record(self, value, record):
        return False if value is None else copy.deepcopy(value)

    # Read format: the value is a list, where each element is a dict containing
    # the definition of a property, together with the property's corresponding
    # value, where relational field values have a display name.
    #
    #       [{
    #           'name': '3adf37f3258cfe40',
    #           'string': 'Color Code',
    #           'type': 'char',
    #           'default': 'blue',
    #           'value': 'red',
    #       }, {
    #           'name': 'aa34746a6851ee4e',
    #           'string': 'Partner',
    #           'type': 'many2one',
    #           'comodel': 'test_new_api.partner',
    #           'value': [1337, 'Bob'],
    #       }]
    #
    def convert_to_read(self, value, record, use_display_name=True):
        return self.convert_to_read_multi([value], record)[0]

    def convert_to_read_multi(self, values, records):
        if not records:
            return values
        assert len(values) == len(records)

        # each value is either False or a dict
        result = []
        for record, value in zip(records, values):
            if definition := self._get_properties_definition(record):
                value = value or {}
                assert isinstance(value, dict), f"Wrong type {value!r}"
                result.append(self._dict_to_list(value, definition))
            else:
                result.append([])

        res_ids_per_model = self._get_res_ids_per_model(records.env, result)

        # value is in record format
        for value in result:
            self._parse_json_types(value, records.env, res_ids_per_model)

        for value in result:
            self._add_display_name(value, records.env)

        return result

    def convert_to_write(self, value, record):
        """If we write a list on the child, update the definition record."""
        return value

    def _get_res_ids_per_model(self, env, values_list):
        """Read everything needed in batch for the given records.

        To retrieve relational properties names, or to check their existence,
        we need to do some SQL queries. To reduce the number of queries when we read
        in batch, we prefetch everything needed before calling
        convert_to_record / convert_to_read.

        Return a dict {model: record_ids} that contains
        the existing ids for each needed models.
        """
        # ids per model we need to fetch in batch to put in cache
        ids_per_model = defaultdict(OrderedSet)

        for record_values in values_list:
            for property_definition in record_values:
                comodel = property_definition.get('comodel')
                type_ = property_definition.get('type')
                property_value = property_definition.get('value') or []
                default = property_definition.get('default') or []

                if type_ not in ('many2one', 'many2many') or comodel not in env:
                    continue

                if type_ == 'many2one':
                    default = [default] if default else []
                    property_value = [property_value] if isinstance(property_value, int) else []
                elif not is_list_of(property_value, int):
                    property_value = []

                ids_per_model[comodel].update(default)
                ids_per_model[comodel].update(property_value)

        # check existence and pre-fetch in batch
        res_ids_per_model = {}
        for model, ids in ids_per_model.items():
            recs = env[model].browse(ids).exists()
            res_ids_per_model[model] = set(recs.ids)

            for record in recs:
                # read a field to pre-fetch the recordset
                with contextlib.suppress(AccessError):
                    record.display_name

        return res_ids_per_model

    def write(self, records, value):
        """Check if the properties definition has been changed.

        To avoid extra SQL queries used to detect definition change, we add a
        flag in the properties list. Parent update is done only when this flag
        is present, delegating the check to the caller (generally web client).

        For deletion, we need to keep the removed property definition in the
        list to be able to put the delete flag in it. Otherwise we have no way
        to know that a property has been removed.
        """
        if isinstance(value, str):
            value = json.loads(value)

        if isinstance(value, dict):
            # don't need to write on the container definition
            return super().write(records, value)

        definition_changed = any(
            definition.get('definition_changed')
            or definition.get('definition_deleted')
            for definition in (value or [])
        )
        if definition_changed:
            value = [
                definition for definition in value
                if not definition.get('definition_deleted')
            ]
            for definition in value:
                definition.pop('definition_changed', None)

            # update the properties definition on the container
            container = records[self.definition_record]
            if container:
                properties_definition = copy.deepcopy(value)
                for property_definition in properties_definition:
                    property_definition.pop('value', None)
                container[self.definition_record_field] = properties_definition

                _logger.info('Properties field: User #%i changed definition of %r', records.env.user.id, container)

        return super().write(records, value)

    def _compute(self, records):
        """Add the default properties value when the container is changed."""
        for record in records:
            record[self.name] = self._add_default_values(
                record.env,
                {self.name: record[self.name], self.definition_record: record[self.definition_record]},
            )

    def _add_default_values(self, env, values):
        """Read the properties definition to add default values.

        Default values are defined on the container in the 'default' key of
        the definition.

        :param env: environment
        :param values: All values that will be written on the record
        :return: Return the default values in the "dict" format
        """
        properties_values = values.get(self.name) or {}

        if not values.get(self.definition_record):
            # container is not given in the value, can not find properties definition
            return {}

        container_id = values[self.definition_record]
        if not isinstance(container_id, (int, BaseModel)):
            raise ValueError(f"Wrong container value {container_id!r}")

        if isinstance(container_id, int):
            # retrieve the container record
            current_model = env[self.model_name]
            definition_record_field = current_model._fields[self.definition_record]
            container_model_name = definition_record_field.comodel_name
            container_id = env[container_model_name].sudo().browse(container_id)

        properties_definition = container_id[self.definition_record_field]
        if not (properties_definition or (
            isinstance(properties_values, list)
            and any(d.get('definition_changed') for d in properties_values)
        )):
            # If a parent is set without properties, we might want to change its definition
            # when we create the new record. But if we just set the value without changing
            # the definition, in that case we can just ignored the passed values
            return {}

        assert isinstance(properties_values, (list, dict))
        if isinstance(properties_values, list):
            self._remove_display_name(properties_values)
            properties_list_values = properties_values
        else:
            properties_list_values = self._dict_to_list(properties_values, properties_definition)

        for properties_value in properties_list_values:
            if properties_value.get('value') is None:
                property_name = properties_value.get('name')
                context_key = f"default_{self.name}.{property_name}"
                if property_name and context_key in env.context:
                    default = env.context[context_key]
                else:
                    default = properties_value.get('default') or False
                properties_value['value'] = default

        return properties_list_values

    def _get_properties_definition(self, record):
        """Return the properties definition of the given record."""
        container = record[self.definition_record]
        if container:
            return container.sudo()[self.definition_record_field]

    @classmethod
    def _add_display_name(cls, values_list, env, value_keys=('value', 'default')):
        """Add the "display_name" for each many2one / many2many properties.

        Modify in place "values_list".

        :param values_list: List of properties definition and values
        :param env: environment
        """
        for property_definition in values_list:
            property_type = property_definition.get('type')
            property_model = property_definition.get('comodel')
            if not property_model:
                continue

            for value_key in value_keys:
                property_value = property_definition.get(value_key)

                if property_type == 'many2one' and property_value and isinstance(property_value, int):
                    try:
                        display_name = env[property_model].browse(property_value).display_name
                        property_definition[value_key] = (property_value, display_name)
                    except AccessError:
                        # protect from access error message, show an empty name
                        property_definition[value_key] = (property_value, None)
                    except MissingError:
                        property_definition[value_key] = False

                elif property_type == 'many2many' and property_value and is_list_of(property_value, int):
                    property_definition[value_key] = []
                    records = env[property_model].browse(property_value)
                    for record in records:
                        try:
                            property_definition[value_key].append((record.id, record.display_name))
                        except AccessError:
                            property_definition[value_key].append((record.id, None))
                        except MissingError:
                            continue

    @classmethod
    def _remove_display_name(cls, values_list, value_key='value'):
        """Remove the display name received by the web client for the relational properties.

        Modify in place "values_list".

        - many2one: (35, 'Bob') -> 35
        - many2many: [(35, 'Bob'), (36, 'Alice')] -> [35, 36]

        :param values_list: List of properties definition with properties value
        :param value_key: In which dict key we need to remove the display name
        """
        for property_definition in values_list:
            if not isinstance(property_definition, dict) or not property_definition.get('name'):
                continue

            property_value = property_definition.get(value_key)
            if not property_value:
                continue

            property_type = property_definition.get('type')

            if property_type == 'many2one' and has_list_types(property_value, [int, (str, NoneType)]):
                property_definition[value_key] = property_value[0]

            elif property_type == 'many2many':
                if is_list_of(property_value, (list, tuple)):
                    # [(35, 'Admin'), (36, 'Demo')] -> [35, 36]
                    property_definition[value_key] = [
                        many2many_value[0]
                        for many2many_value in property_value
                    ]

    @classmethod
    def _add_missing_names(cls, values_list):
        """Generate new properties name if needed.

        Modify in place "values_list".

        :param values_list: List of properties definition with properties value
        """
        for definition in values_list:
            if definition.get('definition_changed') and not definition.get('name'):
                # keep only the first 64 bits
                definition['name'] = str(uuid.uuid4()).replace('-', '')[:16]

    @classmethod
    def _parse_json_types(cls, values_list, env, res_ids_per_model):
        """Parse the value stored in the JSON.

        Check for records existence, if we removed a selection option, ...
        Modify in place "values_list".

        :param values_list: List of properties definition and values
        :param env: environment
        """
        for property_definition in values_list:
            property_value = property_definition.get('value')
            property_type = property_definition.get('type')
            res_model = property_definition.get('comodel')

            if property_type not in cls.ALLOWED_TYPES:
                raise ValueError(f'Wrong property type {property_type!r}')

            if property_type == 'boolean':
                # E.G. convert zero to False
                property_value = bool(property_value)

            elif property_type == 'char' and not isinstance(property_value, str):
                property_value = False

            elif property_value and property_type == 'selection':
                # check if the selection option still exists
                options = property_definition.get('selection') or []
                options = {option[0] for option in options if option or ()}  # always length 2
                if property_value not in options:
                    # maybe the option has been removed on the container
                    property_value = False

            elif property_value and property_type == 'tags':
                # remove all tags that are not defined on the container
                all_tags = {tag[0] for tag in property_definition.get('tags') or ()}
                property_value = [tag for tag in property_value if tag in all_tags]

            elif property_type == 'many2one':
                if not isinstance(property_value, int) \
                        or res_model not in env \
                        or property_value not in res_ids_per_model[res_model]:
                    property_value = False

            elif property_type == 'many2many':
                if not is_list_of(property_value, int):
                    property_value = []

                elif len(property_value) != len(set(property_value)):
                    # remove duplicated value and preserve order
                    property_value = list(dict.fromkeys(property_value))

                property_value = [
                    id_ for id_ in property_value
                    if id_ in res_ids_per_model[res_model]
                ] if res_model in env else []

            elif property_value is None:
                property_value = False

            property_definition['value'] = property_value

    @classmethod
    def _list_to_dict(cls, values_list):
        """Convert a list of properties with definition into a dict {name: value}.

        To not repeat data in database, we only store the value of each property on
        the child. The properties definition is stored on the container.

        E.G.
            Input list:
            [{
                'name': '3adf37f3258cfe40',
                'string': 'Color Code',
                'type': 'char',
                'default': 'blue',
                'value': 'red',
            }, {
                'name': 'aa34746a6851ee4e',
                'string': 'Partner',
                'type': 'many2one',
                'comodel': 'test_new_api.partner',
                'value': [1337, 'Bob'],
            }]

            Output dict:
            {
                '3adf37f3258cfe40': 'red',
                'aa34746a6851ee4e': 1337,
            }

        :param values_list: List of properties definition and value
        :return: Generate a dict {name: value} from this definitions / values list
        """
        if not is_list_of(values_list, dict):
            raise ValueError(f'Wrong properties value {values_list!r}')

        cls._add_missing_names(values_list)

        dict_value = {}
        for property_definition in values_list:
            property_value = property_definition.get('value')
            property_type = property_definition.get('type')
            property_model = property_definition.get('comodel')

            if property_type == 'separator':
                # "separator" is used as a visual separator in the form view UI
                # it does not have a value and does not need to be stored on children
                continue
            if property_type not in ('integer', 'float') or property_value != 0:
                property_value = property_value or False
            if property_type in ('many2one', 'many2many') and property_model and property_value:
                # check that value are correct before storing them in database
                if property_type == 'many2many' and property_value and not is_list_of(property_value, int):
                    raise ValueError(f"Wrong many2many value {property_value!r}")

                if property_type == 'many2one' and not isinstance(property_value, int):
                    raise ValueError(f"Wrong many2one value {property_value!r}")

            dict_value[property_definition['name']] = property_value

        return dict_value

    @classmethod
    def _dict_to_list(cls, values_dict, properties_definition):
        """Convert a dict of {property: value} into a list of property definition with values.

        :param values_dict: JSON value coming from the child table
        :param properties_definition: Properties definition coming from the container table
        :return: Merge both value into a list of properties with value
            Ignore every values in the child that is not defined on the container.
        """
        if not is_list_of(properties_definition, dict):
            raise ValueError(f'Wrong properties value {properties_definition!r}')

        values_list = copy.deepcopy(properties_definition)
        for property_definition in values_list:
            property_definition['value'] = values_dict.get(property_definition['name'])
        return values_list

    def property_to_sql(self, field_sql: SQL, property_name: str, model: BaseModel, alias: str, query: Query) -> SQL:
        check_property_field_value_name(property_name)
        return SQL("(%s -> %s)", field_sql, property_name)

    def condition_to_sql(self, field_expr: str, operator: str, value, model: BaseModel, alias: str, query: Query) -> SQL:
        fname, property_name = parse_field_expr(field_expr)
        if not property_name:
            raise ValueError(f"Missing property name for {self}")
        raw_sql_field = model._field_to_sql(alias, fname, query)
        sql_left = model._field_to_sql(alias, field_expr, query)

        if operator in ('=', '!='):
            operator = 'in' if operator == '=' else 'not in'
            value = [value]
        if operator in ('in', 'not in'):
            assert isinstance(value, COLLECTION_TYPES)
            if len(value) == 1 and True in value:
                # inverse the condition
                check_null_op_false = "!=" if operator == 'in' else "="
                value = []
                operator = 'in' if operator == 'not in' else 'not in'
            elif False in value:
                check_null_op_false = "=" if operator == 'in' else "!="
                value = [v for v in value if v]
            else:
                value = list(value)
                check_null_op_false = None

            sqls = []
            if check_null_op_false:
                sqls.append(SQL(
                    "%s%s'%s'",
                    sql_left,
                    SQL_OPERATORS[check_null_op_false],
                    False,
                ))
                if check_null_op_false == '=':
                    # check null value too
                    sqls.extend((
                        SQL("%s IS NULL", raw_sql_field),
                        SQL("NOT (%s ? %s)", raw_sql_field, property_name),
                    ))
            # left can be an array or a single value!
            # Even if we use the '=' operator, we must check the list subset.
            # There is an unsupported edge-case where left is a list and we
            # have multiple values.
            if len(value) == 1:
                # check single value equality
                sql_operator = SQL_OPERATORS['=' if operator == 'in' else '!=']
                sql_right = SQL("%s", json.dumps(value[0]))
                sqls.append(SQL("%s%s%s", sql_left, sql_operator, sql_right))
            if value:
                sql_not = SQL('NOT ') if operator == 'not in' else SQL()
                # hackish operator to search values
                if len(value) > 1:
                    # left <@ value_list -- single left value in value_list
                    # (here we suppose left is a single value)
                    sql_operator = SQL(" <@ ")
                else:
                    # left @> value -- value_list in left
                    sql_operator = SQL(" @> ")
                sql_right = SQL("%s", json.dumps(value))
                sqls.append(SQL(
                    "%s%s%s%s",
                    sql_not, sql_left, sql_operator, sql_right,
                ))
            assert sqls, "No SQL generated for property"
            if len(sqls) == 1:
                return sqls[0]
            combine_sql = SQL(" OR ") if operator == 'in' else SQL(" AND ")
            return SQL("(%s)", combine_sql.join(sqls))

        sql_operator = SQL_OPERATORS[operator]
        if operator in ('ilike', 'not ilike'):
            value = f'%{value}%'
            unaccent = model.env.registry.unaccent
        else:
            unaccent = lambda x: x  # noqa: E731

        if isinstance(value, str):
            sql_left = SQL("(%s ->> %s)", raw_sql_field, property_name)  # JSONified value
            sql_right = SQL("%s", value)
            return SQL(
                "%s%s%s",
                unaccent(sql_left), sql_operator, unaccent(sql_right),
            )

        sql_right = SQL("%s", json.dumps(value))
        return SQL(
            "%s%s%s",
            unaccent(sql_left), sql_operator, unaccent(sql_right),
        )


class PropertiesDefinition(Field):
    """ Field used to define the properties definition (see :class:`~odoo.fields.Properties`
    field). This field is used on the container record to define the structure
    of expected properties on subrecords. It is used to check the properties
    definition. """
    type = 'properties_definition'
    _column_type = ('jsonb', 'jsonb')
    copy = True                         # containers may act like templates, keep definitions to ease usage
    readonly = False
    prefetch = True

    REQUIRED_KEYS = ('name', 'type')
    ALLOWED_KEYS = (
        'name', 'string', 'type', 'comodel', 'default',
        'selection', 'tags', 'domain', 'view_in_cards',
    )
    # those keys will be removed if the types does not match
    PROPERTY_PARAMETERS_MAP = {
        'comodel': {'many2one', 'many2many'},
        'domain': {'many2one', 'many2many'},
        'selection': {'selection'},
        'tags': {'tags'},
    }

    def convert_to_column(self, value, record, values=None, validate=True):
        """Convert the value before inserting it in database.

        This method accepts a list properties definition.

        The relational properties (many2one / many2many) default value
        might contain the display_name of those records (and will be removed).

        [{
            'name': '3adf37f3258cfe40',
            'string': 'Color Code',
            'type': 'char',
            'default': 'blue',
            'default': 'red',
        }, {
            'name': 'aa34746a6851ee4e',
            'string': 'Partner',
            'type': 'many2one',
            'comodel': 'test_new_api.partner',
            'default': [1337, 'Bob'],
        }]
        """
        if not value:
            return None

        if isinstance(value, str):
            value = json.loads(value)

        if not isinstance(value, list):
            raise ValueError(f'Wrong properties definition type {type(value)!r}')

        if validate:
            Properties._remove_display_name(value, value_key='default')

            self._validate_properties_definition(value, record.env)

        return json.dumps(value)

    def convert_to_cache(self, value, record, validate=True):
        # any format -> cache format (list of dicts or None)
        if not value:
            return None

        if isinstance(value, list):
            # avoid accidental side effects from shared mutable data, and make
            # the value strict with respect to JSON (tuple -> list, etc)
            value = json.dumps(value)

        if isinstance(value, str):
            value = json.loads(value)

        if not isinstance(value, list):
            raise ValueError(f'Wrong properties definition type {type(value)!r}')

        if validate:
            Properties._remove_display_name(value, value_key='default')

            self._validate_properties_definition(value, record.env)

        return value

    def convert_to_record(self, value, record):
        # cache format -> record format (list of dicts)
        if not value:
            return []

        # return a copy of the definition in cache where all property
        # definitions have been cleaned up
        result = []

        for property_definition in value:
            if not all(property_definition.get(key) for key in self.REQUIRED_KEYS):
                # some required keys are missing, ignore this property definition
                continue

            # don't modify the value in cache
            property_definition = copy.deepcopy(property_definition)

            type_ = property_definition.get('type')

            if type_ in ('many2one', 'many2many'):
                # check if the model still exists in the environment, the module of the
                # model might have been uninstalled so the model might not exist anymore
                property_model = property_definition.get('comodel')
                if property_model not in record.env:
                    property_definition['comodel'] = False
                    property_definition.pop('domain', None)
                elif property_domain := property_definition.get('domain'):
                    # some fields in the domain might have been removed
                    # (e.g. if the module has been uninstalled)
                    # check if the domain is still valid
                    try:
                        dom = Domain(ast.literal_eval(property_domain))
                        model = record.env[property_model]
                        dom.validate(model)
                    except ValueError:
                        del property_definition['domain']

            elif type_ in ('selection', 'tags'):
                # always set at least an empty array if there's no option
                property_definition[type_] = property_definition.get(type_) or []

            result.append(property_definition)

        return result

    def convert_to_read(self, value, record, use_display_name=True):
        # record format -> read format (list of dicts with display names)
        if not value:
            return value

        if use_display_name:
            Properties._add_display_name(value, record.env, value_keys=('default',))

        return value

    def convert_to_write(self, value, record):
        return value

    @classmethod
    def _validate_properties_definition(cls, properties_definition, env):
        """Raise an error if the property definition is not valid."""
        properties_names = set()

        for property_definition in properties_definition:
            for property_parameter, allowed_types in cls.PROPERTY_PARAMETERS_MAP.items():
                if property_definition.get('type') not in allowed_types and property_parameter in property_definition:
                    raise ValueError(f'Invalid property parameter {property_parameter!r}')

            property_definition_keys = set(property_definition.keys())

            invalid_keys = property_definition_keys - set(cls.ALLOWED_KEYS)
            if invalid_keys:
                raise ValueError(
                    'Some key are not allowed for a properties definition [%s].' %
                    ', '.join(invalid_keys),
                )

            check_property_field_value_name(property_definition['name'])

            required_keys = set(cls.REQUIRED_KEYS) - property_definition_keys
            if required_keys:
                raise ValueError(
                    'Some key are missing for a properties definition [%s].' %
                    ', '.join(required_keys),
                )

            property_name = property_definition.get('name')
            if not property_name or property_name in properties_names:
                raise ValueError(f'The property name {property_name!r} is not set or duplicated.')
            properties_names.add(property_name)

            property_type = property_definition.get('type')
            if property_type and property_type not in Properties.ALLOWED_TYPES:
                raise ValueError(f'Wrong property type {property_type!r}.')

            model = property_definition.get('comodel')
            if model and (model not in env or env[model].is_transient() or env[model]._abstract):
                raise ValueError(f'Invalid model name {model!r}')

            property_selection = property_definition.get('selection')
            if property_selection:
                if (not is_list_of(property_selection, (list, tuple))
                   or not all(len(selection) == 2 for selection in property_selection)):
                    raise ValueError(f'Wrong options {property_selection!r}.')

                all_options = [option[0] for option in property_selection]
                if len(all_options) != len(set(all_options)):
                    duplicated = set(filter(lambda x: all_options.count(x) > 1, all_options))
                    raise ValueError(f'Some options are duplicated: {", ".join(duplicated)}.')

            property_tags = property_definition.get('tags')
            if property_tags:
                if (not is_list_of(property_tags, (list, tuple))
                   or not all(len(tag) == 3 and isinstance(tag[2], int) for tag in property_tags)):
                    raise ValueError(f'Wrong tags definition {property_tags!r}.')

                all_tags = [tag[0] for tag in property_tags]
                if len(all_tags) != len(set(all_tags)):
                    duplicated = set(filter(lambda x: all_tags.count(x) > 1, all_tags))
                    raise ValueError(f'Some tags are duplicated: {", ".join(duplicated)}.')
