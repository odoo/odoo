import csv
import itertools

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from openerp.osv import orm, fields
from openerp.tools.translate import _

FIELDS_RECURSION_LIMIT = 2
class ir_import(orm.TransientModel):
    _name = 'base_import.import'

    _columns = {
        'res_model': fields.char('Model', size=64),
        'file': fields.binary('File'),
        'file_name': fields.char('File Name', size=None),
    }

    def get_fields(self, cr, uid, model, context=None,
                   depth=FIELDS_RECURSION_LIMIT):
        """ Recursively get fields for the provided model (through
        fields_get) and filter them according to importability

        The output format is a list of ``Field``, with ``Field``
        defined as:

        .. class:: Field

            .. attribute:: id (str)

                A non-unique identifier for the field, used to compute
                the span of the ``required`` attribute: if multiple
                ``required`` fields have the same id, only one of them
                is necessary.

            .. attribute:: name (str)

                The field's logical (OpenERP) name within the scope of
                its parent.

            .. attribute:: string (str)

                The field's human-readable name (``@string``)

            .. attribute:: required (bool)

                Whether the field is marked as required in the
                model. Clients must provide non-empty import values
                for all required fields or the import will error out.

            .. attribute:: fields (list(Field))

                The current field's subfields. The database and
                external identifiers for m2o and m2m fields; a
                filtered and transformed fields_get for o2m fields (to
                a variable depth defined by ``depth``).

                Fields with no sub-fields will have an empty list of
                sub-fields.

        :param str model: name of the model to get fields form
        :param int landing: depth of recursion into o2m fields
        """
        fields = [{
            'id': 'id',
            'name': 'id',
            'string': _("External ID"),
            'required': False,
            'fields': [],
        }]
        fields_got = self.pool[model].fields_get(cr, uid, context=context)
        for name, field in fields_got.iteritems():
            if field.get('readonly'):
                states = field.get('states')
                if not states:
                    continue
                # states = {state: [(attr, value), (attr2, value2)], state2:...}
                if not any(attr == 'readonly' and value is False
                           for attr, value in itertools.chain.from_iterable(
                                states.itervalues())):
                    continue

            f = {
                'id': name,
                'name': name,
                'string': field['string'],
                # Y U NO ALWAYS HAVE REQUIRED
                'required': bool(field.get('required')),
                'fields': [],
            }

            if field['type'] in ('many2many', 'many2one'):
                f['fields'] = [
                    dict(f, name='id', string=_("External ID")),
                    dict(f, name='.id', string=_("Database ID")),
                ]
            elif field['type'] == 'one2many' and depth:
                f['fields'] = self.get_fields(
                    cr, uid, field['relation'], context=context, depth=depth-1)

            fields.append(f)

        return fields

    def parse_preview(self, cr, uid, id, options, count=10, context=None):
        """ Generates a preview of the uploaded files, and performs
        fields-matching between the import's file data and the model's
        columns.

        :param id: identifier of the import
        :param int count: number of preview lines to generate
        :param dict options: format-specific options
        :returns: (fields, matches, preview)
        :rtype: (dict(str: dict(...)), dict(str, str), list(list(str)))
        """
        record = self.browse(cr, uid, id, context=context)
        # recursive fields_get (cache based on res_model?)
        fields = record.get_fields(record.res_model)
        import pprint
        pprint.pprint(fields)
        # extract title row?
        #    match title row to fields_ge
        # Extract first $count rows
        # return triplet
