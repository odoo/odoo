import base64
import codecs
import csv
import itertools
import logging
import operator
import random

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from openerp.osv import orm, fields
from openerp.tools.translate import _

FIELDS_RECURSION_LIMIT = 2
ERROR_PREVIEW_BYTES = 200
_logger = logging.getLogger(__name__)
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

        # TODO: cache on model?
        return fields

    def _read_csv(self, record, options):
        """ Returns a CSV-parsed iterator of all empty lines in the file

        :throws csv.Error: if an error is detected during CSV parsing
        :throws UnicodeDecodeError: if ``options.encoding`` is incorrect
        """
        csv_iterator = csv.reader(
            StringIO(base64.b64decode(record.file)),
            quotechar=options['quote'],
            delimiter=options['separator'])
        csv_nonempty = itertools.ifilter(None, csv_iterator)
        # TODO: guess encoding?
        encoding = options.get('encoding', 'utf-8')
        return itertools.imap(
            lambda row: [item.decode(encoding) for item in row],
            csv_nonempty)

    def _match_header(self, header, fields, options):
        """ Attempts to match a given header to a field of the
        imported model.

        :param str header: header name from the CSV file
        :param fields:
        :param dict options:
        :returns: an empty list if the header couldn't be matched, or
                  all the fields to traverse
        :rtype: list(Field)
        """
        for field in fields:
            # FIXME: should match all translations & original
            # TODO: use string distance (levenshtein? hamming?)
            if header == field['name'] \
              or header.lower() == field['string'].lower():
                return [field]

        if '/' not in header:
            return []

        # relational field path
        traversal = []
        subfields = fields
        # Iteratively dive into fields tree
        for section in header.split('/'):
            # Strip section in case spaces are added around '/' for
            # readability of paths
            match = self._match_header(section.strip(), subfields, options)
            # Any match failure, exit
            if not match: return []
            # prep subfields for next iteration within match[0]
            field = match[0]
            subfields = field['fields']
            traversal.append(field)
        return traversal

    def _match_headers(self, rows, fields, options):
        """ Attempts to match the imported model's fields to the
        titles of the parsed CSV file, if the file is supposed to have
        headers.

        Will consume the first line of the ``rows`` iterator.

        Returns either None (no title) or a dict mapping cell indices
        to key paths in the ``fields`` tree

        :param Iterator rows:
        :param dict fields:
        :param dict options:
        :rtype: None | dict(int: list(str))
        """
        if not options.get('headers'):
            return None

        headers = next(rows)
        return dict(
            (index, [field['name'] for field in self._match_header(header, fields, options)] or None)
            for index, header in enumerate(headers)
        )

    def parse_preview(self, cr, uid, id, options, count=10, context=None):
        """ Generates a preview of the uploaded files, and performs
        fields-matching between the import's file data and the model's
        columns.

        :param id: identifier of the import
        :param int count: number of preview lines to generate
        :param options: format-specific options.
                        CSV: {encoding, quote, separator, headers}
        :type options: {str, str, str, bool}
        :returns: {fields, matches, preview} | {error, preview}
        :rtype: {dict(str: dict(...)), dict(int, list(str)), list(list(str))} | {str, str}
        """
        (record,) = self.browse(cr, uid, [id], context=context)
        fields = self.get_fields(cr, uid, record.res_model, context=context)

        try:
            rows = self._read_csv(record, options)

            match = self._match_headers(rows, fields, options)
            # Match should have consumed the first row (iif headers), get
            # the ``count`` next rows for preview
            preview = itertools.islice(rows, count)
            return {
                'fields': fields,
                'matches': match,
                'preview': list(preview),
            }
        except (TypeError, UnicodeDecodeError), e:
            # Due to lazy generators, UnicodeDecodeError (for
            # instance) may only be raised when serializing the
            # preview to a list in the return.
            _logger.debug("Error during CSV parsing preview", exc_info=True)
            return {
                'error': _("Failed to parse CSV file: %s") % e,
                # iso-8859-1 ensures decoding will always succeed,
                # even if it yields non-printable characters. This is
                # in case of UnicodeDecodeError (or csv.Error
                # compounded with UnicodeDecodeError)
                'preview': base64.b64decode(record.file)[:ERROR_PREVIEW_BYTES]\
                                 .decode('iso-8859-1'),
            }

    def _convert_import_data(self, record, fields, options, context=None):
        """ Extracts the input browse_record and fields list (with
        ``False``-y placeholders for fields to *not* import) into a
        format Model.import_data can use: a fields list without holes
        and the precisely matching data matrix

        :param browse_record record:
        :param list(str|bool): fields
        :returns: (data, fields)
        :rtype: (list(list(str)), list(str))
        """
        # Get indices for non-empty fields
        indices = [index for index, field in enumerate(fields) if field]
        # If only one index, itemgetter will return an atom rather
        # than a 1-tuple
        if len(indices) == 1: mapper = lambda row: [row[indices[0]]]
        else: mapper = operator.itemgetter(*indices)
        # Get only list of actually imported fields
        import_fields = filter(None, fields)

        rows_to_import = self._read_csv(record, options)
        if options.get('headers'):
            rows_to_import = itertools.islice(
                rows_to_import, 1, None)
        data = [
            row for row in itertools.imap(mapper, rows_to_import)
            # don't try inserting completely empty rows (e.g. from
            # filtering out o2m fields)
            if any(row)
        ]

        return data, import_fields

    def do(self, cr, uid, id, fields, options, dryrun=False, context=None):
        """ Actual execution of the import

        :param fields: import mapping: maps each column to a field,
                       ``False`` for the columns to ignore
        :type fields: list(str|bool)
        :param dict options:
        :param bool dryrun: performs all import operations (and
                            validations) but rollbacks writes, allows
                            getting as much errors as possible without
                            the risk of clobbering the database.
        :returns: A list of errors. If the list is empty the import
                  executed fully and correctly. If the list is
                  non-empty it contains dicts with 3 keys ``type`` the
                  type of error (``error|warning``); ``message`` the
                  error message associated with the error (a string)
                  and ``record`` the data which failed to import (or
                  ``false`` if that data isn't available or provided)
        :rtype: list({type, message, record})
        """
        cr.execute('SAVEPOINT import')

        (record,) = self.browse(cr, uid, [id], context=context)
        data, import_fields = self._convert_import_data(
            record, fields, options, context=context)

        try:
            (code, record, message, _wat) = self.pool[record.res_model].import_data(
                cr, uid, import_fields, data, context=context)
        except Exception, e:
            # TODO: remove when exceptions stop being an "expected"
            #       behavior of import_data on some invalid input.
            code, record, message = -1, None, str(e)

        if dryrun:
            cr.execute('ROLLBACK TO SAVEPOINT import')
        else:
            cr.execute('RELEASE SAVEPOINT import')

        if code != -1:
            return []

        # TODO: add key for error location?
        # TODO: error not within normal preview, how to display? Re-preview
        #       with higher count?
        return [{
            'type': 'error',
            'message': message,
            'record': record or False
        }]
