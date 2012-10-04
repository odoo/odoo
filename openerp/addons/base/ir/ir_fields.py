# -*- coding: utf-8 -*-
import functools
import operator
import itertools
import psycopg2
import time
from openerp.osv import orm, fields
from openerp.tools.translate import _
from openerp.tools.misc import DEFAULT_SERVER_DATE_FORMAT,\
                               DEFAULT_SERVER_DATETIME_FORMAT

REFERENCING_FIELDS = set([None, 'id', '.id'])
def only_ref_fields(record):
    return dict((k, v) for k, v in record.iteritems()
                if k in REFERENCING_FIELDS)
def exclude_ref_fields(record):
    return dict((k, v) for k, v in record.iteritems()
                if k not in REFERENCING_FIELDS)

CREATE = lambda values: (0, False, values)
UPDATE = lambda id, values: (1, id, values)
DELETE = lambda id: (2, id, False)
FORGET = lambda id: (3, id, False)
LINK_TO = lambda id: (4, id, False)
DELETE_ALL = lambda: (5, False, False)
REPLACE_WITH = lambda ids: (6, False, ids)

class ConversionNotFound(ValueError): pass

class ir_fields_converter(orm.Model):
    _name = 'ir.fields.converter'

    def to_field(self, cr, uid, model, column, fromtype=str, context=None):
        """ Fetches a converter for the provided column object, from the
        specified type.

        A converter is simply a callable taking a value of type ``fromtype``
        (or a composite of ``fromtype``, e.g. list or dict) and returning a
        value acceptable for a write() on the column ``column``.

        By default, tries to get a method on itself with a name matching the
        pattern ``_$fromtype_$column._type`` and returns it.

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
        instance of :class:`~openerp.osv.orm.ImportWarning` to the second value
        it returns. The handling of a warning at the upper levels is the same
        as ``ValueError`` above.

        :param cr: openerp cursor
        :param uid: ID of user calling the converter
        :param column: column object to generate a value for
        :type column: :class:`fields._column`
        :param type fromtype: type to convert to something fitting for ``column``
        :param context: openerp request context
        :return: a function (fromtype -> column.write_type), if a converter is found
        :rtype: Callable | None
        """
        # FIXME: return None
        converter = getattr(
            self, '_%s_to_%s' % (fromtype.__name__, column._type), None)
        if not converter: return None

        return functools.partial(
            converter, cr, uid, model, column, context=context)

    def _str_to_boolean(self, cr, uid, model, column, value, context=None):
        # all translatables used for booleans
        true, yes, false, no = _(u"true"), _(u"yes"), _(u"false"), _(u"no")
        # potentially broken casefolding? What about locales?
        trues = set(word.lower() for word in itertools.chain(
            [u'1', u"true", u"yes"], # don't use potentially translated values
            self._get_translations(cr, uid, ['code'], u"true", context=context),
            self._get_translations(cr, uid, ['code'], u"yes", context=context),
        ))
        if value.lower() in trues: return True, []

        # potentially broken casefolding? What about locales?
        falses = set(word.lower() for word in itertools.chain(
            [u'', u"0", u"false", u"no"],
            self._get_translations(cr, uid, ['code'], u"false", context=context),
            self._get_translations(cr, uid, ['code'], u"no", context=context),
        ))
        if value.lower() in falses: return False, []

        return True, [orm.ImportWarning(
            _(u"Unknown value '%s' for boolean field '%%(field)s', assuming '%s'")
                % (value, yes), {
                'moreinfo': _(u"Use '1' for yes and '0' for no")
            })]

    def _str_to_integer(self, cr, uid, model, column, value, context=None):
        try:
            return int(value), []
        except ValueError:
            raise ValueError(
                _(u"'%s' does not seem to be an integer for field '%%(field)s'")
                % value)

    def _str_to_float(self, cr, uid, model, column, value, context=None):
        try:
            return float(value), []
        except ValueError:
            raise ValueError(
                _(u"'%s' does not seem to be a number for field '%%(field)s'")
                % value)

    def _str_id(self, cr, uid, model, column, value, context=None):
        return value, []
    _str_to_char = _str_to_text = _str_to_binary = _str_id

    def _str_to_date(self, cr, uid, model, column, value, context=None):
        try:
            time.strptime(value, DEFAULT_SERVER_DATE_FORMAT)
            return value, []
        except ValueError:
            raise ValueError(
                _(u"'%s' does not seem to be a valid date for field '%%(field)s'") % value, {
                    'moreinfo': _(u"Use the format '%s'") % u"2012-12-31"
                })

    def _str_to_datetime(self, cr, uid, model, column, value, context=None):
        try:
            time.strptime(value, DEFAULT_SERVER_DATETIME_FORMAT)
            return value, []
        except ValueError:
            raise ValueError(
                _(u"'%s' does not seem to be a valid datetime for field '%%(field)s'") % value, {
                    'moreinfo': _(u"Use the format '%s'") % u"2012-12-31 23:59:59"
                })

    def _get_translations(self, cr, uid, types, src, context):
        types = tuple(types)
        # Cache translations so they don't have to be reloaded from scratch on
        # every row of the file
        tnx_cache = cr.cache.setdefault(self._name, {})
        if tnx_cache.setdefault(types, {}) and src in tnx_cache[types]:
            return tnx_cache[types][src]

        Translations = self.pool['ir.translation']
        tnx_ids = Translations.search(
            cr, uid, [('type', 'in', types), ('src', '=', src)], context=context)
        tnx = Translations.read(cr, uid, tnx_ids, ['value'], context=context)
        result = tnx_cache[types][src] = map(operator.itemgetter('value'), tnx)
        return result

    def _str_to_selection(self, cr, uid, model, column, value, context=None):

        selection = column.selection
        if not isinstance(selection, (tuple, list)):
            # FIXME: Don't pass context to avoid translations?
            #        Or just copy context & remove lang?
            selection = selection(model, cr, uid)
        for item, label in selection:
            labels = self._get_translations(
                cr, uid, ('selection', 'model', 'code'), label, context=context)
            labels.append(label)
            if value == unicode(item) or value in labels:
                return item, []
        raise ValueError(
            _(u"Value '%s' not found in selection field '%%(field)s'") % (
                value), {
                'moreinfo': [label or unicode(item) for item, label in selection
                             if label or item]
            })


    def db_id_for(self, cr, uid, model, column, subfield, value, context=None):
        """ Finds a database id for the reference ``value`` in the referencing
        subfield ``subfield`` of the provided column of the provided model.

        :param cr: OpenERP cursor
        :param uid: OpenERP user id
        :param model: model to which the column belongs
        :param column: relational column for which references are provided
        :param subfield: a relational subfield allowing building of refs to
                         existing records: ``None`` for a name_get/name_search,
                         ``id`` for an external id and ``.id`` for a database
                         id
        :param value: value of the reference to match to an actual record
        :param context: OpenERP request context
        :return: a pair of the matched database identifier (if any), the
                 translated user-readable name for the field and the list of
                 warnings
        :rtype: (ID|None, unicode, list)
        """
        if context is None: context = {}
        id = None
        warnings = []
        extras = {'moreinfo': {
            'type': 'ir.actions.act_window', 'target': 'new',
            'res_model': column._obj, 'view_mode': 'tree,form',
            'view_type': 'form',
            'views': [(False, 'tree', (False, 'form'))],
            'help': _(u"See all possible values")
        }}
        RelatedModel = self.pool[column._obj]
        if subfield == '.id':
            field_type = _(u"database id")
            try: tentative_id = int(value)
            except ValueError: tentative_id = value
            try:
                if RelatedModel.search(cr, uid, [('id', '=', tentative_id)],
                                       context=context):
                    id = tentative_id
            except psycopg2.DataError:
                # type error
                raise ValueError(
                    _(u"Invalid database id '%s' for the field '%%(field)s'") % value,
                    extras)
        elif subfield == 'id':
            field_type = _(u"external id")
            if '.' in value:
                module, xid = value.split('.', 1)
            else:
                module, xid = context.get('_import_current_module', ''), value
            ModelData = self.pool['ir.model.data']
            try:
                md_id = ModelData._get_id(cr, uid, module, xid)
                model_data = ModelData.read(cr, uid, [md_id], ['res_id'],
                                            context=context)
                if model_data:
                    id = model_data[0]['res_id']
            except ValueError: pass # leave id is None
        elif subfield is None:
            field_type = _(u"name")
            ids = RelatedModel.name_search(
                cr, uid, name=value, operator='=', context=context)
            if ids:
                if len(ids) > 1:
                    warnings.append(orm.ImportWarning(
                        _(u"Found multiple matches for field '%%(field)s' (%d matches)")
                        % (len(ids))))
                id, _name = ids[0]
        else:
            raise Exception(u"Unknown sub-field '%s'" % subfield)

        if id is None:
            raise ValueError(
                _(u"No matching record found for %(field_type)s '%(value)s' in field '%%(field)s'")
                % {'field_type': field_type, 'value': value}, extras)
        return id, field_type, warnings

    def _referencing_subfield(self, record):
        """ Checks the record for the subfields allowing referencing (an
        existing record in an other table), errors out if it finds potential
        conflicts (multiple referencing subfields) or non-referencing subfields
        returns the name of the correct subfield.

        :param record:
        :return: the record subfield to use for referencing and a list of warnings
        :rtype: str, list
        """
        # Can import by name_get, external id or database id
        fieldset = set(record.iterkeys())
        if fieldset - REFERENCING_FIELDS:
            raise ValueError(
                _(u"Can not create Many-To-One records indirectly, import the field separately"))
        if len(fieldset) > 1:
            raise ValueError(
                _(u"Ambiguous specification for field '%(field)s', only provide one of name, external id or database id"))

        # only one field left possible, unpack
        [subfield] = fieldset
        return subfield, []

    def _str_to_many2one(self, cr, uid, model, column, values, context=None):
        # Should only be one record, unpack
        [record] = values

        subfield, w1 = self._referencing_subfield(record)

        reference = record[subfield]
        id, subfield_type, w2 = self.db_id_for(
            cr, uid, model, column, subfield, reference, context=context)
        return id, w1 + w2

    def _str_to_many2many(self, cr, uid, model, column, value, context=None):
        [record] = value

        subfield, warnings = self._referencing_subfield(record)

        ids = []
        for reference in record[subfield].split(','):
            id, subfield_type, ws = self.db_id_for(
                cr, uid, model, column, subfield, reference, context=context)
            ids.append(id)
            warnings.extend(ws)
        return [(6, 0, ids)], warnings

    def _str_to_one2many(self, cr, uid, model, column, records, context=None):
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

        for record in records:
            id = None
            refs = only_ref_fields(record)
            # there are ref fields in the record
            if refs:
                subfield, w1 = self._referencing_subfield(refs)
                warnings.extend(w1)
                reference = record[subfield]
                id, subfield_type, w2 = self.db_id_for(
                    cr, uid, model, column, subfield, reference, context=context)
                warnings.extend(w2)

            writable = exclude_ref_fields(record)
            if id:
                commands.append(LINK_TO(id))
                commands.append(UPDATE(id, writable))
            else:
                commands.append(CREATE(writable))

        return commands, warnings
