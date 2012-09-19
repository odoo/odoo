# -*- coding: utf-8 -*-
import functools
import operator
import warnings
from openerp.osv import orm, fields
from openerp.tools.translate import _

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
            self, '_%s_to_%s' % (fromtype.__name__, column._type))
        if not converter: return None

        return functools.partial(
            converter, cr, uid, model, column, context=context)

    def _str_to_boolean(self, cr, uid, model, column, value, context=None):
        return value.lower() not in ('', '0', 'false', 'off')

    def _str_to_integer(self, cr, uid, model, column, value, context=None):
        if not value: return False
        return int(value)

    def _str_to_float(self, cr, uid, model, column, value, context=None):
        if not value: return False
        return float(value)

    def _str_to_char(self, cr, uid, model, column, value, context=None):
        return value or False

    def _str_to_text(self, cr, uid, model, column, value, context=None):
        return value or False

    def _get_translations(self, cr, uid, types, src, context):
        Translations = self.pool['ir.translation']
        tnx_ids = Translations.search(
            cr, uid, [('type', 'in', types), ('src', '=', src)], context=context)
        tnx = Translations.read(cr, uid, tnx_ids, ['value'], context=context)
        return map(operator.itemgetter('value'), tnx)
    def _str_to_selection(self, cr, uid, model, column, value, context=None):

        selection = column.selection
        if not isinstance(selection, (tuple, list)):
            # FIXME: Don't pass context to avoid translations?
            #        Or just copy context & remove lang?
            selection = selection(model, cr, uid)
        for item, label in selection:
            labels = self._get_translations(
                cr, uid, ('selection', 'model'), label, context=context)
            labels.append(label)
            if value == unicode(item) or value in labels:
                return item
        raise ValueError(
            _(u"Value '%s' not found in selection field '%%(field)s'") % (
                value))


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
        :return: a pair of the matched database identifier (if any) and the
                 translated user-readable name for the field
        :rtype: (ID|None, unicode)
        """
        id = None
        RelatedModel = self.pool[column._obj]
        if subfield == '.id':
            field_type = _(u"database id")
            try: tentative_id = int(value)
            except ValueError: tentative_id = value
            if RelatedModel.search(cr, uid, [('id', '=', tentative_id)],
                                   context=context):
                id = tentative_id
        elif subfield == 'id':
            field_type = _(u"external id")
            if '.' in value:
                module, xid = value.split('.', 1)
            else:
                module, xid = '', value
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
                    warnings.warn(
                        _(u"Found multiple matches for field '%%(field)s' (%d matches)")
                        % (len(ids)), orm.ImportWarning)
                id, _name = ids[0]
        else:
            raise Exception(u"Unknown sub-field '%s'" % subfield)
        return id, field_type

    def _referencing_subfield(self, record):
        """ Checks the record for the subfields allowing referencing (an
        existing record in an other table), errors out if it finds potential
        conflicts (multiple referencing subfields) or non-referencing subfields
        returns the name of the correct subfield.

        :param record:
        :return: the record subfield to use for referencing
        :rtype: str
        """
        # Can import by name_get, external id or database id
        allowed_fields = set([None, 'id', '.id'])
        fieldset = set(record.iterkeys())
        if fieldset - allowed_fields:
            raise ValueError(
                _(u"Can not create Many-To-One records indirectly, import the field separately"))
        if len(fieldset) > 1:
            raise ValueError(
                _(u"Ambiguous specification for field '%(field)s', only provide one of name, external id or database id"))

        # only one field left possible, unpack
        [subfield] = fieldset
        return subfield

    def _str_to_many2one(self, cr, uid, model, column, values, context=None):
        # Should only be one record, unpack
        [record] = values

        subfield = self._referencing_subfield(record)

        reference = record[subfield]
        id, subfield_type = self.db_id_for(
            cr, uid, model, column, subfield, reference, context=context)

        if id is None:
            raise ValueError(
                _(u"No matching record found for %(field_type)s '%(value)s' in field '%%(field)s'")
                % {'field_type': subfield_type, 'value': reference})
        return id
    def _str_to_many2many(self, cr, uid, model, column, value, context=None):
        [record] = value

        subfield = self._referencing_subfield(record)

        ids = []
        for reference in record[subfield].split(','):
            id, subfield_type = self.db_id_for(
                cr, uid, model, column, subfield, reference, context=context)
            if id is None:
                raise ValueError(
                    _(u"No matching record found for %(field_type)s '%(value)s' in field '%%(field)s'")
                    % {'field_type': subfield_type, 'value': reference})
            ids.append(id)

        return [(6, 0, ids)]
    def _str_to_one2many(self, cr, uid, model, column, value, context=None):
        return value
