# -*- coding: utf-8 -*-
import cStringIO
import datetime
import functools
import operator
import itertools
import time

import psycopg2
import pytz

from openerp.osv import orm
from openerp.tools.translate import _
from openerp.tools.misc import DEFAULT_SERVER_DATE_FORMAT,\
                               DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools import html_sanitize

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

class ImportWarning(Warning):
    """ Used to send warnings upwards the stack during the import process """
    pass

class ConversionNotFound(ValueError): pass

class ColumnWrapper(object):
    def __init__(self, column, cr, uid, pool, fromtype, context=None):
        self._converter = None
        self._column = column
        if column._obj:
            self._pool = pool
            self._converter_args = {
                'cr': cr,
                'uid': uid,
                'model': pool[column._obj],
                'fromtype': fromtype,
                'context': context
            }
    @property
    def converter(self):
        if not self._converter:
            self._converter = self._pool['ir.fields.converter'].for_model(
                **self._converter_args)
        return self._converter

    def __getattr__(self, item):
        return getattr(self._column, item)

class ir_fields_converter(orm.Model):
    _name = 'ir.fields.converter'

    def for_model(self, cr, uid, model, fromtype=str, context=None):
        """ Returns a converter object for the model. A converter is a
        callable taking a record-ish (a dictionary representing an openerp
        record with values of typetag ``fromtype``) and returning a converted
        records matching what :meth:`openerp.osv.orm.Model.write` expects.

        :param model: :class:`openerp.osv.orm.Model` for the conversion base
        :returns: a converter callable
        :rtype: (record: dict, logger: (field, error) -> None) -> dict
        """
        columns = dict(
            (k, ColumnWrapper(v.column, cr, uid, self.pool, fromtype, context))
            for k, v in model._all_columns.iteritems())
        converters = dict(
            (k, self.to_field(cr, uid, model, column, fromtype, context))
            for k, column in columns.iteritems())

        def fn(record, log):
            converted = {}
            for field, value in record.iteritems():
                if field in (None, 'id', '.id'): continue
                if not value:
                    converted[field] = False
                    continue
                try:
                    converted[field], ws = converters[field](value)
                    for w in ws:
                        if isinstance(w, basestring):
                            # wrap warning string in an ImportWarning for
                            # uniform handling
                            w = ImportWarning(w)
                        log(field, w)
                except ValueError, e:
                    log(field, e)

            return converted
        return fn

    def to_field(self, cr, uid, model, column, fromtype=str, context=None):
        """ Fetches a converter for the provided column object, from the
        specified type.

        A converter is simply a callable taking a value of type ``fromtype``
        (or a composite of ``fromtype``, e.g. list or dict) and returning a
        value acceptable for a write() on the column ``column``.

        By default, tries to get a method on itself with a name matching the
        pattern ``_$fromtype_to_$column._type`` and returns it.

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

        :param column: column object to generate a value for
        :type column: :class:`fields._column`
        :param fromtype: type to convert to something fitting for ``column``
        :type fromtype: type | str
        :param context: openerp request context
        :return: a function (fromtype -> column.write_type), if a converter is found
        :rtype: Callable | None
        """
        assert isinstance(fromtype, (type, str))
        # FIXME: return None
        typename = fromtype.__name__ if isinstance(fromtype, type) else fromtype
        converter = getattr(
            self, '_%s_to_%s' % (typename, column._type), None)
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

        return True, [ImportWarning(
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
    _str_to_reference = _str_to_char = _str_to_text = _str_to_binary = _str_to_html = _str_id

    def _str_to_date(self, cr, uid, model, column, value, context=None):
        try:
            time.strptime(value, DEFAULT_SERVER_DATE_FORMAT)
            return value, []
        except ValueError:
            raise ValueError(
                _(u"'%s' does not seem to be a valid date for field '%%(field)s'") % value, {
                    'moreinfo': _(u"Use the format '%s'") % u"2012-12-31"
                })

    def _input_tz(self, cr, uid, context):
        # if there's a tz in context, try to use that
        if context.get('tz'):
            try:
                return pytz.timezone(context['tz'])
            except pytz.UnknownTimeZoneError:
                pass

        # if the current user has a tz set, try to use that
        user = self.pool['res.users'].read(
            cr, uid, [uid], ['tz'], context=context)[0]
        if user['tz']:
            try:
                return pytz.timezone(user['tz'])
            except pytz.UnknownTimeZoneError:
                pass

        # fallback if no tz in context or on user: UTC
        return pytz.UTC

    def _str_to_datetime(self, cr, uid, model, column, value, context=None):
        if context is None: context = {}
        try:
            parsed_value = datetime.datetime.strptime(
                value, DEFAULT_SERVER_DATETIME_FORMAT)
        except ValueError:
            raise ValueError(
                _(u"'%s' does not seem to be a valid datetime for field '%%(field)s'") % value, {
                    'moreinfo': _(u"Use the format '%s'") % u"2012-12-31 23:59:59"
                })

        input_tz = self._input_tz(cr, uid, context)# Apply input tz to the parsed naive datetime
        dt = input_tz.localize(parsed_value, is_dst=False)
        # And convert to UTC before reformatting for writing
        return dt.astimezone(pytz.UTC).strftime(DEFAULT_SERVER_DATETIME_FORMAT), []

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
            selection = selection(model, cr, uid, context=None)
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
        action = {'type': 'ir.actions.act_window', 'target': 'new',
                  'view_mode': 'tree,form', 'view_type': 'form',
                  'views': [(False, 'tree'), (False, 'form')],
                  'help': _(u"See all possible values")}
        if subfield is None:
            action['res_model'] = column._obj
        elif subfield in ('id', '.id'):
            action['res_model'] = 'ir.model.data'
            action['domain'] = [('model', '=', column._obj)]

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
                    {'moreinfo': action})
        elif subfield == 'id':
            field_type = _(u"external id")
            if '.' in value:
                module, xid = value.split('.', 1)
            else:
                module, xid = context.get('_import_current_module', ''), value
            ModelData = self.pool['ir.model.data']
            try:
                _model, id = ModelData.get_object_reference(
                    cr, uid, module, xid)
            except ValueError: pass # leave id is None
        elif subfield is None:
            field_type = _(u"name")
            ids = RelatedModel.name_search(
                cr, uid, name=value, operator='=', context=context)
            if ids:
                if len(ids) > 1:
                    warnings.append(ImportWarning(
                        _(u"Found multiple matches for field '%%(field)s' (%d matches)")
                        % (len(ids))))
                id, _name = ids[0]
        else:
            raise Exception(_(u"Unknown sub-field '%s'") % subfield)

        if id is None:
            raise ValueError(
                _(u"No matching record found for %(field_type)s '%(value)s' in field '%%(field)s'")
                % {'field_type': field_type, 'value': value},
                {'moreinfo': action})
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
        return [REPLACE_WITH(ids)], warnings

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

        def log(_, e):
            if not isinstance(e, Warning):
                raise e
            warnings.append(e)
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

            writable = column.converter(exclude_ref_fields(record), log)
            if id:
                commands.append(LINK_TO(id))
                commands.append(UPDATE(id, writable))
            else:
                commands.append(CREATE(writable))

        return commands, warnings
