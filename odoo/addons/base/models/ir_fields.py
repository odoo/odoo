# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import functools
import itertools
from typing import NamedTuple

import pytz

from odoo import api, Command, fields, models
from odoo.tools import OrderedSet
from odoo.tools.translate import _, code_translations, LazyTranslate

_lt = LazyTranslate(__name__)

REFERENCING_FIELDS = {None, 'id', '.id'}
def only_ref_fields(record):
    return {k: v for k, v in record.items() if k in REFERENCING_FIELDS}
def exclude_ref_fields(record):
    return {k: v for k, v in record.items() if k not in REFERENCING_FIELDS}

# these lazy translations promise translations for ['yes', 'no', 'true', 'false']
BOOLEAN_TRANSLATIONS = (
    _lt('yes'),
    _lt('no'),
    _lt('true'),
    _lt('false')
)


class FakeField(NamedTuple):
    comodel_name: str
    name: str


class ImportWarning(Warning):
    """ Used to send warnings upwards the stack during the import process """
    pass

class ConversionNotFound(ValueError):
    pass


class IrFieldsConverter(models.AbstractModel):
    _name = 'ir.fields.converter'
    _description = 'Fields Converter'

    @api.model
    def _format_import_error(self, error_type, error_msg, error_params=(), error_args=None):
        # sanitize error params for later formatting by the import system
        sanitize = lambda p: p.replace('%', '%%') if isinstance(p, str) else p
        if error_params:
            if isinstance(error_params, str):
                error_params = sanitize(error_params)
            elif isinstance(error_params, dict):
                error_params = {k: sanitize(v) for k, v in error_params.items()}
            elif isinstance(error_params, tuple):
                error_params = tuple(sanitize(v) for v in error_params)
        return error_type(error_msg % error_params, error_args)

    def _get_import_field_path(self, field, value):
        """ Rebuild field path for import error attribution to the right field.
        This method uses the 'parent_fields_hierarchy' context key built during treatment of one2many fields
        (_str_to_one2many). As the field to import is the last of the chain (child_id/child_id2/field_to_import),
        we need to retrieve the complete hierarchy in case of error in order to assign the error to the correct
        column in the import UI.

        :param (str) field: field in which the value will be imported.
        :param (str or list) value:
            - str: in most of the case the value we want to import into a field is a string (or a number).
            - list: when importing into a one2may field, all the records to import are regrouped into a list of dict.
                E.g.: creating multiple partners: [{None: 'ChildA_1', 'type': 'Private address'}, {None: 'ChildA_2', 'type': 'Private address'}]
                where 'None' is the name. (because we can find a partner by his name, we don't need to specify the field.)

        The field_path value is computed based on the last field in the chain.
        for example,

            - path_field for 'Private address' at childA_1 is ['partner_id', 'type']
            - path_field for 'childA_1' is ['partner_id']

        So, by retrieving the correct field_path for each value to import, if errors are raised for those fields,
        we can the link the errors to the correct header-field couple in the import UI.
        """
        field_path = [field]
        parent_fields_hierarchy = self.env.context.get('parent_fields_hierarchy')
        if parent_fields_hierarchy:
            field_path = parent_fields_hierarchy + field_path

        field_path_value = value
        while isinstance(field_path_value, list):
            key = list(field_path_value[0].keys())[0]
            if key:
                field_path.append(key)
            field_path_value = field_path_value[0][key]
        return field_path

    @api.model
    def for_model(self, model, fromtype=str, *, savepoint):
        """ Returns a converter object for the model. A converter is a
        callable taking a record-ish (a dictionary representing an odoo
        record with values of typetag ``fromtype``) and returning a converted
        records matching what :meth:`odoo.models.Model.write` expects.

        :param model: :class:`odoo.models.Model` for the conversion base
        :param fromtype:
        :param savepoint: savepoint to rollback to on error
        :returns: a converter callable
        :rtype: (record: dict, logger: (field, error) -> None) -> dict
        """
        # make sure model is new api
        model = self.env[model._name]

        converters = {
            name: self.to_field(model, field, fromtype, savepoint=savepoint)
            for name, field in model._fields.items()
        }

        def fn(record, log):
            converted = {}
            import_file_context = self.env.context.get('import_file')
            for field, value in record.items():
                if field in REFERENCING_FIELDS:
                    continue
                if not value:
                    converted[field] = False
                    continue
                try:
                    converted[field], ws = converters[field](value)
                    for w in ws:
                        if isinstance(w, str):
                            # wrap warning string in an ImportWarning for
                            # uniform handling
                            w = ImportWarning(w)
                        log(field, w)
                except (UnicodeEncodeError, UnicodeDecodeError) as e:
                    log(field, ValueError(str(e)))
                except ValueError as e:
                    if import_file_context:
                        # if the error is linked to a matching error, the error is a tuple
                        # E.g.:("Value X cannot be found for field Y at row 1", {
                        #   'more_info': {},
                        #   'value': 'X',
                        #   'field': 'Y',
                        #   'field_path': child_id/Y,
                        # })
                        # In order to link the error to the correct header-field couple in the import UI, we need to add
                        # the field path to the additional error info.
                        # As we raise the deepest child in error, we need to add the field path only for the deepest
                        # error in the import recursion. (if field_path is given, don't overwrite it)
                        error_info = len(e.args) > 1 and e.args[1]
                        if error_info and not error_info.get('field_path'):  # only raise the deepest child in error
                            error_info['field_path'] = self._get_import_field_path(field, value)
                    log(field, e)
            return converted

        return fn

    @api.model
    def to_field(self, model, field, fromtype=str, *, savepoint):
        """ Fetches a converter for the provided field object, from the
        specified type.

        A converter is simply a callable taking a value of type ``fromtype``
        (or a composite of ``fromtype``, e.g. list or dict) and returning a
        value acceptable for a write() on the field ``field``.

        By default, tries to get a method on itself with a name matching the
        pattern ``_$fromtype_to_$field.type`` and returns it.

        Converter callables can either return a value and a list of warnings
        to their caller or raise ``ValueError``, which will be interpreted as a
        validation & conversion failure.

        ValueError can have either one or two parameters. The first parameter
        is mandatory, **must** be a unicode string and will be used as the
        user-visible message for the error (it should be translatable and
        translated). It can contain a ``field`` named format placeholder so the
        caller can inject the field's translated, user-facing name (@string).

        The second parameter is optional and, if provided, must be a mapping.
        This mapping will be merged into the error dictionary returned to the
        client.

        If a converter can perform its function but has to make assumptions
        about the data, it can send a warning to the user through adding an
        instance of :class:`~.ImportWarning` to the second value
        it returns. The handling of a warning at the upper levels is the same
        as ``ValueError`` above.

        :param model:
        :param field: field object to generate a value for
        :type field: :class:`odoo.fields.Field`
        :param fromtype: type to convert to something fitting for ``field``
        :type fromtype: type | str
        :param savepoint: savepoint to rollback to on errors
        :return: a function (fromtype -> field.write_type), if a converter is found
        :rtype: Callable | None
        """
        assert isinstance(fromtype, (type, str))
        # FIXME: return None
        typename = fromtype.__name__ if isinstance(fromtype, type) else fromtype
        converter = getattr(self, '_%s_to_%s' % (typename, field.type), None)
        if not converter:
            return None
        return functools.partial(converter, model, field, savepoint=savepoint)

    def _str_to_json(self, model, field, value, savepoint):
        try:
            return json.loads(value), []
        except ValueError:
            msg = self.env._("'%s' does not seem to be a valid JSON for field '%%(field)s'")
            raise self._format_import_error(ValueError, msg, value)

    def _str_to_properties(self, model, field, value, savepoint):

        # If we want to import the all properties at once (with the technical value)
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                msg = self.env._("Unable to import'%%(field)s' Properties field as a whole, target individual property instead.")
                raise self._format_import_error(ValueError, msg)

        if not isinstance(value, list):
            msg = self.env._("Unable to import'%%(field)s' Properties field as a whole, target individual property instead.")
            raise self._format_import_error(ValueError, msg, {'value': value})

        warnings = []
        for property_dict in value:
            if not (property_dict.keys() >= {'name', 'type', 'string'}):
                msg = self.env._("'%(value)s' does not seem to be a valid Property value for field '%%(field)s'. Each property need at least 'name', 'type' and 'string' attribute.")
                raise self._format_import_error(ValueError, msg, {'value': property_dict})

            val = property_dict.get('value')
            if not val:
                continue

            property_type = property_dict['type']

            if property_type == 'selection':
                # either label or the technical value
                new_val = next(iter(
                    sel_val for sel_val, sel_label in property_dict['selection']
                    if val in (sel_val, sel_label)
                ), None)
                if not new_val:
                    msg = self.env._("'%(value)s' does not seem to be a valid Selection value for '%(label_property)s' (subfield of '%%(field)s' field).")
                    raise self._format_import_error(ValueError, msg, {'value': val, 'label_property': property_dict['string']})
                property_dict['value'] = new_val

            elif property_type == 'tags':
                tags = val.split(',')
                new_val = []
                for tag in tags:
                    val_tag = next(iter(
                        tag_val for tag_val, tag_label, _color in property_dict['tags']
                        if tag in (tag_val, tag_label)
                    ), None)
                    if not val_tag:
                        msg = self.env._("'%(value)s' does not seem to be a valid Tag value for '%(label_property)s' (subfield of '%%(field)s' field).")
                        raise self._format_import_error(ValueError, msg, {'value': tag, 'label_property': property_dict['string']})
                    new_val.append(val_tag)
                property_dict['value'] = new_val

            elif property_type == 'boolean':
                new_val, warnings = self._str_to_boolean(model, field, val, savepoint=savepoint)
                if not warnings:
                    property_dict['value'] = new_val
                else:
                    msg = self.env._("Unknown value '%(value)s' for boolean '%(label_property)s' property (subfield of '%%(field)s' field).")
                    raise self._format_import_error(ValueError, msg, {'value': val, 'label_property': property_dict['string']})

            elif property_type in ('many2one', 'many2many'):
                [record] = property_dict['value']

                subfield, w1 = self._referencing_subfield(record)
                if w1:
                    warnings.append(w1)

                values = record[subfield]

                references = values.split(',') if property_type == 'many2many' else [values]
                ids = []
                fake_field = FakeField(comodel_name=property_dict['comodel'], name=property_dict['string'])
                for reference in references:
                    id_, ws = self.db_id_for(model, fake_field, subfield, reference, savepoint)
                    ids.append(id_)
                    warnings.extend(ws)

                property_dict['value'] = ids if property_type == 'many2many' else ids[0]

            elif property_type == 'integer':
                try:
                    property_dict['value'] = int(val)
                except ValueError:
                    msg = self.env._("'%(value)s' does not seem to be an integer for field '%(label_property)s' property (subfield of '%%(field)s' field).")
                    raise self._format_import_error(ValueError, msg, {'value': val, 'label_property': property_dict['string']})

            elif property_type == 'float':
                try:
                    property_dict['value'] = float(val)
                except ValueError:
                    msg = self.env._("'%(value)s' does not seem to be an float for field '%(label_property)s' property (subfield of '%%(field)s' field).")
                    raise self._format_import_error(ValueError, msg, {'value': val, 'label_property': property_dict['string']})

        return value, warnings

    @api.model
    def _str_to_boolean(self, model, field, value, savepoint):
        # all translatables used for booleans
        # potentially broken casefolding? What about locales?
        trues = set(word.lower() for word in itertools.chain(
            [u'1', u"true", u"yes"], # don't use potentially translated values
            self._get_boolean_translations(u"true"),
            self._get_boolean_translations(u"yes"),
        ))
        if value.lower() in trues:
            return True, []

        # potentially broken casefolding? What about locales?
        falses = set(word.lower() for word in itertools.chain(
            [u'', u"0", u"false", u"no"],
            self._get_boolean_translations(u"false"),
            self._get_boolean_translations(u"no"),
        ))
        if value.lower() in falses:
            return False, []

        if field.name in self.env.context.get('import_skip_records', []):
            return None, []

        return True, [self._format_import_error(
            ValueError,
            self.env._("Unknown value '%s' for boolean field '%%(field)s'"),
            value,
            {'moreinfo': self.env._("Use '1' for yes and '0' for no")}
        )]

    @api.model
    def _str_to_integer(self, model, field, value, savepoint):
        try:
            return int(value), []
        except ValueError:
            raise self._format_import_error(
                ValueError,
                self.env._("'%s' does not seem to be an integer for field '%%(field)s'"),
                value
            )

    @api.model
    def _str_to_float(self, model, field, value, savepoint):
        try:
            return float(value), []
        except ValueError:
            raise self._format_import_error(
                ValueError,
                self.env._("'%s' does not seem to be a number for field '%%(field)s'"),
                value
            )

    _str_to_monetary = _str_to_float

    @api.model
    def _str_id(self, model, field, value, savepoint):
        return value, []

    _str_to_reference = _str_to_char = _str_to_text = _str_to_binary = _str_to_html = _str_id

    @api.model
    def _str_to_date(self, model, field, value, savepoint):
        try:
            parsed_value = fields.Date.from_string(value)
            return fields.Date.to_string(parsed_value), []
        except ValueError:
            raise self._format_import_error(
                ValueError,
                self.env._("'%s' does not seem to be a valid date for field '%%(field)s'"),
                value,
                {'moreinfo': self.env._("Use the format '%s'", u"2012-12-31")}
            )

    @api.model
    def _input_tz(self):
        return self.env.tz

    @api.model
    def _str_to_datetime(self, model, field, value, savepoint):
        try:
            parsed_value = fields.Datetime.from_string(value)
        except ValueError:
            raise self._format_import_error(
                ValueError,
                self.env._("'%s' does not seem to be a valid datetime for field '%%(field)s'"),
                value,
                {'moreinfo': self.env._("Use the format '%s'", u"2012-12-31 23:59:59")}
            )

        input_tz = self._input_tz()# Apply input tz to the parsed naive datetime
        dt = input_tz.localize(parsed_value, is_dst=False)
        # And convert to UTC before reformatting for writing
        return fields.Datetime.to_string(dt.astimezone(pytz.UTC)), []

    @api.model
    def _get_boolean_translations(self, src):
        # Cache translations so they don't have to be reloaded from scratch on
        # every row of the file
        tnx_cache = self.env.cr.cache.setdefault(self._name, {})
        if src in tnx_cache:
            return tnx_cache[src]

        values = OrderedSet()
        for lang, __ in self.env['res.lang'].get_installed():
            translations = code_translations.get_python_translations('base', lang)
            if src in translations:
                values.add(translations[src])

        result = tnx_cache[src] = list(values)
        return result

    @api.model
    def _get_selection_translations(self, field, src):
        if not src:
            return []
        # Cache translations so they don't have to be reloaded from scratch on
        # every row of the file
        tnx_cache = self.env.cr.cache.setdefault(self._name, {})
        if src in tnx_cache:
            return tnx_cache[src]

        values = OrderedSet()
        self.env['ir.model.fields.selection'].flush_model()
        query = """
            SELECT s.name
            FROM ir_model_fields_selection s
            JOIN ir_model_fields f ON s.field_id = f.id
            WHERE f.model = %s AND f.name = %s AND s.name->>'en_US' = %s
        """
        self.env.cr.execute(query, [field.model_name, field.name, src])
        for (name,) in self.env.cr.fetchall():
            name.pop('en_US')
            values.update(name.values())

        result = tnx_cache[src] = list(values)
        return result

    @api.model
    def _str_to_selection(self, model, field, value, savepoint):
        # get untranslated values
        env = self.with_context(lang=None).env
        selection = field.get_description(env)['selection']

        for item, label in selection:
            if callable(field.selection):
                labels = [label]
                for item2, label2 in field._description_selection(self.env):
                    if item2 == item:
                        labels.append(label2)
                        break
            else:
                labels = [label] + self._get_selection_translations(field, label)
            # case insensitive comparaison of string to allow to set the value even if the given 'value' param is not
            # exactly (case sensitive) the same as one of the selection item.
            if value.lower() == str(item).lower() or any(value.lower() == label.lower() for label in labels):
                return item, []

        if field.name in self.env.context.get('import_skip_records', []):
            return None, []
        elif field.name in self.env.context.get('import_set_empty_fields', []):
            return False, []
        raise self._format_import_error(
            ValueError,
            self.env._("Value '%s' not found in selection field '%%(field)s'"),
            value,
            {'moreinfo': [_label or str(item) for item, _label in selection if _label or item]}
        )

    @api.model
    def db_id_for(self, model, field, subfield, value, savepoint):
        """ Finds a database id for the reference ``value`` in the referencing
        subfield ``subfield`` of the provided field of the provided model.

        :param model: model to which the field belongs
        :param field: relational field for which references are provided
        :param subfield: a relational subfield allowing building of refs to
                         existing records: ``None`` for a name_search,
                         ``id`` for an external id and ``.id`` for a database
                         id
        :param value: value of the reference to match to an actual record
        :param savepoint: savepoint for rollback on errors
        :return: a pair of the matched database identifier (if any), the
                 translated user-readable name for the field and the list of
                 warnings
        :rtype: (ID|None, unicode, list)
        """
        # the function 'flush' comes from BaseModel.load(), and forces the
        # creation/update of former records (batch creation)
        flush = self.env.context.get('import_flush', lambda **kw: None)

        id = None
        warnings = []
        error_msg = ''
        action = {
            'name': 'Possible Values',
            'type': 'ir.actions.act_window', 'target': 'new',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'context': {'create': False},
            'help': self.env._("See all possible values")}
        if subfield is None:
            action['res_model'] = field.comodel_name
        elif subfield in ('id', '.id'):
            action['res_model'] = 'ir.model.data'
            action['domain'] = [('model', '=', field.comodel_name)]

        RelatedModel = self.env[field.comodel_name]
        if subfield == '.id':
            field_type = self.env._("database id")
            if isinstance(value, str) and not self._str_to_boolean(model, field, value, savepoint=savepoint)[0]:
                return False, warnings
            try:
                tentative_id = int(value)
            except ValueError:
                raise self._format_import_error(
                    ValueError,
                    self.env._("Invalid database id '%s' for the field '%%(field)s'"),
                    value,
                    {'moreinfo': action})
            if RelatedModel.browse(tentative_id).exists():
                id = tentative_id
        elif subfield == 'id':
            field_type = self.env._("external id")
            if not self._str_to_boolean(model, field, value, savepoint=savepoint)[0]:
                return False, warnings
            if '.' in value:
                xmlid = value
            else:
                xmlid = "%s.%s" % (self.env.context.get('_import_current_module', ''), value)
            flush(xml_id=xmlid)
            id = self._xmlid_to_record_id(xmlid, RelatedModel)
        elif subfield is None:
            field_type = self.env._("name")
            if value == '':
                return False, warnings
            flush(model=field.comodel_name)
            ids = RelatedModel.name_search(name=value, operator='=')
            if ids:
                if len(ids) > 1:
                    warnings.append(ImportWarning(_(
                        'Found multiple matches for value "%(value)s" in field "%%(field)s" (%(match_count)s matches)',
                        value=str(value).replace('%', '%%'),
                        match_count=len(ids),
                    )))
                id, _name = ids[0]
            else:
                name_create_enabled_fields = self.env.context.get('name_create_enabled_fields') or {}
                if name_create_enabled_fields.get(field.name):
                    try:
                        id, _name = RelatedModel.name_create(name=value)
                        RelatedModel.env.flush_all()
                    except Exception:  # noqa: BLE001
                        savepoint.rollback()
                        error_msg = self.env._("Cannot create new '%s' records from their name alone. Please create those records manually and try importing again.", RelatedModel._description)
        else:
            raise self._format_import_error(
                Exception,
                self.env._("Unknown sub-field “%s”", subfield),
            )

        set_empty = False
        skip_record = False
        if self.env.context.get('import_file'):
            import_set_empty_fields = self.env.context.get('import_set_empty_fields') or []
            field_path = "/".join((self.env.context.get('parent_fields_hierarchy', []) + [field.name]))
            set_empty = field_path in import_set_empty_fields
            skip_record = field_path in self.env.context.get('import_skip_records', [])
        if id is None and not set_empty and not skip_record:
            if error_msg:
                message = self.env._("No matching record found for %(field_type)s '%(value)s' in field '%%(field)s' and the following error was encountered when we attempted to create one: %(error_message)s")
            else:
                message = self.env._("No matching record found for %(field_type)s '%(value)s' in field '%%(field)s'")

            error_info_dict = {'moreinfo': action}
            if self.env.context.get('import_file'):
                # limit to 50 char to avoid too long error messages.
                value = value[:50] if isinstance(value, str) else value
                error_info_dict.update({'value': value, 'field_type': field_type})
                if error_msg:
                    error_info_dict['error_message'] = error_msg
            raise self._format_import_error(
                ValueError,
                message,
                {'field_type': field_type, 'value': value, 'error_message': error_msg},
                error_info_dict)
        return id, warnings

    def _xmlid_to_record_id(self, xmlid, model):
        """ Return the record id corresponding to the given external id,
        provided that the record actually exists; otherwise return ``None``.
        """
        import_cache = self.env.context.get('import_cache', {})
        result = import_cache.get(xmlid)

        if not result:
            module, name = xmlid.split('.', 1)
            query = """
                SELECT d.model, d.res_id
                FROM ir_model_data d
                JOIN "{}" r ON d.res_id = r.id
                WHERE d.module = %s AND d.name = %s
            """.format(model._table)
            self.env.cr.execute(query, [module, name])
            result = self.env.cr.fetchone()

        if result:
            res_model, res_id = import_cache[xmlid] = result
            if res_model != model._name:
                MSG = "Invalid external ID %s: expected model %r, found %r"
                raise ValueError(MSG % (xmlid, model._name, res_model))
            return res_id

    def _referencing_subfield(self, record):
        """ Checks the record for the subfields allowing referencing (an
        existing record in an other table), errors out if it finds potential
        conflicts (multiple referencing subfields) or non-referencing subfields
        returns the name of the correct subfield.

        :param record:
        :return: the record subfield to use for referencing and a list of warnings
        :rtype: str, list
        """
        # Can import by display_name, external id or database id
        fieldset = set(record)
        if fieldset - REFERENCING_FIELDS:
            raise ValueError(
                self.env._("Can not create Many-To-One records indirectly, import the field separately"))
        if len(fieldset) > 1:
            raise ValueError(
                self.env._("Ambiguous specification for field '%(field)s', only provide one of name, external id or database id"))

        # only one field left possible, unpack
        [subfield] = fieldset
        return subfield, []

    @api.model
    def _str_to_many2one(self, model, field, values, savepoint):
        # Should only be one record, unpack
        [record] = values

        subfield, w1 = self._referencing_subfield(record)

        id, w2 = self.db_id_for(model, field, subfield, record[subfield], savepoint)
        return id, w1 + w2

    @api.model
    def _str_to_many2one_reference(self, model, field, value, savepoint):
        return self._str_to_integer(model, field, value, savepoint)

    @api.model
    def _str_to_many2many(self, model, field, value, savepoint):
        [record] = value

        subfield, warnings = self._referencing_subfield(record)

        ids = []
        for reference in record[subfield].split(','):
            id, ws = self.db_id_for(model, field, subfield, reference, savepoint)
            ids.append(id)
            warnings.extend(ws)

        if field.name in self.env.context.get('import_set_empty_fields', []) and any(id is None for id in ids):
            ids = [id for id in ids if id]
        elif field.name in self.env.context.get('import_skip_records', []) and any(id is None for id in ids):
            return None, warnings

        if self.env.context.get('update_many2many'):
            return [Command.link(id) for id in ids], warnings
        else:
            return [Command.set(ids)], warnings

    @api.model
    def _str_to_one2many(self, model, field, records, savepoint):
        name_create_enabled_fields = self.env.context.get('name_create_enabled_fields') or {}
        prefix = field.name + '/'
        relative_name_create_enabled_fields = {
            k[len(prefix):]: v
            for k, v in name_create_enabled_fields.items()
            if k.startswith(prefix)
        }
        commands = []
        warnings = []

        if len(records) == 1 and exclude_ref_fields(records[0]) == {}:
            # only one row with only ref field, field=ref1,ref2,ref3 as in
            # m2o/m2m
            record = records[0]
            subfield, ws = self._referencing_subfield(record)
            warnings.extend(ws)
            # transform [{subfield:ref1,ref2,ref3}] into
            # [{subfield:ref1},{subfield:ref2},{subfield:ref3}]
            records = ({subfield:item} for item in record[subfield].split(','))

        def log(f, exception):
            if not isinstance(exception, Warning):
                current_field_name = self.env[field.comodel_name]._fields[f].string
                arg0 = exception.args[0].replace('%(field)s', '%(field)s/' + current_field_name)
                exception.args = (arg0, *exception.args[1:])
                raise exception
            warnings.append(exception)

        # Complete the field hierarchy path
        # E.g. For "parent/child/subchild", field hierarchy path for "subchild" is ['parent', 'child']
        parent_fields_hierarchy = self.env.context.get('parent_fields_hierarchy', []) + [field.name]

        convert = self.with_context(
            name_create_enabled_fields=relative_name_create_enabled_fields,
            parent_fields_hierarchy=parent_fields_hierarchy
        ).for_model(self.env[field.comodel_name], savepoint=savepoint)

        for record in records:
            id = None
            refs = only_ref_fields(record)
            writable = convert(exclude_ref_fields(record), log)
            if refs:
                subfield, w1 = self._referencing_subfield(refs)
                warnings.extend(w1)
                try:
                    id, w2 = self.db_id_for(model, field, subfield, record[subfield], savepoint)
                    warnings.extend(w2)
                except ValueError:
                    if subfield != 'id':
                        raise
                    writable['id'] = record['id']

            if id:
                commands.append(Command.link(id))
                commands.append(Command.update(id, writable))
            else:
                commands.append(Command.create(writable))

        return commands, warnings
