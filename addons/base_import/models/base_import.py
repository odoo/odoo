# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import csv
import datetime
import io
import itertools
import logging
import psycopg2
import operator
import os
import re

from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.tools.mimetypes import guess_mimetype
from odoo.tools.misc import ustr
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, pycompat

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


FIELDS_RECURSION_LIMIT = 2
ERROR_PREVIEW_BYTES = 200
_logger = logging.getLogger(__name__)

try:
    import xlrd
    try:
        from xlrd import xlsx
    except ImportError:
        xlsx = None
except ImportError:
    xlrd = xlsx = None

try:
    from . import odf_ods_reader
except ImportError:
    odf_ods_reader = None

FILE_TYPE_DICT = {
    'text/csv': ('csv', True, None),
    'application/vnd.ms-excel': ('xls', xlrd, 'xlrd'),
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ('xlsx', xlsx, 'xlrd >= 0.8'),
    'application/vnd.oasis.opendocument.spreadsheet': ('ods', odf_ods_reader, 'odfpy')
}
EXTENSIONS = {
    '.' + ext: handler
    for mime, (ext, handler, req) in pycompat.items(FILE_TYPE_DICT)
}


class Import(models.TransientModel):

    _name = 'base_import.import'

    # allow imports to survive for 12h in case user is slow
    _transient_max_hours = 12.0

    res_model = fields.Char('Model')
    file = fields.Binary('File', help="File to check and/or import, raw binary (not base64)")
    file_name = fields.Char('File Name')
    file_type = fields.Char('File Type')

    @api.model
    def get_fields(self, model, depth=FIELDS_RECURSION_LIMIT):
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

                The field's logical (Odoo) name within the scope of
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
        Model = self.env[model]
        importable_fields = [{
            'id': 'id',
            'name': 'id',
            'string': _("External ID"),
            'required': False,
            'fields': [],
            'type': 'id',
        }]
        model_fields = Model.fields_get()
        blacklist = models.MAGIC_COLUMNS + [Model.CONCURRENCY_CHECK_FIELD]
        for name, field in pycompat.items(model_fields):
            if name in blacklist:
                continue
            # an empty string means the field is deprecated, @deprecated must
            # be absent or False to mean not-deprecated
            if field.get('deprecated', False) is not False:
                continue
            if field.get('readonly'):
                states = field.get('states')
                if not states:
                    continue
                # states = {state: [(attr, value), (attr2, value2)], state2:...}
                if not any(attr == 'readonly' and value is False
                           for attr, value in itertools.chain.from_iterable(pycompat.values(states))):
                    continue
            field_value = {
                'id': name,
                'name': name,
                'string': field['string'],
                # Y U NO ALWAYS HAS REQUIRED
                'required': bool(field.get('required')),
                'fields': [],
                'type': field['type'],
            }

            if field['type'] in ('many2many', 'many2one'):
                field_value['fields'] = [
                    dict(field_value, name='id', string=_("External ID"), type='id'),
                    dict(field_value, name='.id', string=_("Database ID"), type='id'),
                ]
            elif field['type'] == 'one2many' and depth:
                field_value['fields'] = self.get_fields(field['relation'], depth=depth-1)
                if self.user_has_groups('base.group_no_one'):
                    field_value['fields'].append({'id': '.id', 'name': '.id', 'string': _("Database ID"), 'required': False, 'fields': [], 'type': 'id'})

            importable_fields.append(field_value)

        # TODO: cache on model?
        return importable_fields

    @api.multi
    def _read_file(self, options):
        """ Dispatch to specific method to read file content, according to its mimetype or file type
            :param options : dict of reading options (quoting, separator, ...)
        """
        self.ensure_one()
        # guess mimetype from file content
        mimetype = guess_mimetype(self.file)
        (file_extension, handler, req) = FILE_TYPE_DICT.get(mimetype, (None, None, None))
        if handler:
            try:
                return getattr(self, '_read_' + file_extension)(options)
            except Exception:
                _logger.warn("Failed to read file '%s' (transient id %d) using guessed mimetype %s", self.file_name or '<unknown>', self.id, mimetype)

        # try reading with user-provided mimetype
        (file_extension, handler, req) = FILE_TYPE_DICT.get(self.file_type, (None, None, None))
        if handler:
            try:
                return getattr(self, '_read_' + file_extension)(options)
            except Exception:
                _logger.warn("Failed to read file '%s' (transient id %d) using user-provided mimetype %s", self.file_name or '<unknown>', self.id, self.file_type)

        # fallback on file extensions as mime types can be unreliable (e.g.
        # software setting incorrect mime types, or non-installed software
        # leading to browser not sending mime types)
        if self.file_name:
            p, ext = os.path.splitext(self.file_name)
            if ext in EXTENSIONS:
                try:
                    return getattr(self, '_read_' + ext[1:])(options)
                except Exception:
                    _logger.warn("Failed to read file '%s' (transient id %s) using file extension", self.file_name, self.id)

        if req:
            raise ImportError(_("Unable to load \"{extension}\" file: requires Python module \"{modname}\"").format(extension=file_extension, modname=req))
        raise ValueError(_("Unsupported file format \"{}\", import only supports CSV, ODS, XLS and XLSX").format(self.file_type))

    @api.multi
    def _read_xls(self, options):
        """ Read file content, using xlrd lib """
        book = xlrd.open_workbook(file_contents=self.file)
        return self._read_xls_book(book)

    def _read_xls_book(self, book):
        sheet = book.sheet_by_index(0)
        # emulate Sheet.get_rows for pre-0.9.4
        for row in pycompat.imap(sheet.row, range(sheet.nrows)):
            values = []
            for cell in row:
                if cell.ctype is xlrd.XL_CELL_NUMBER:
                    is_float = cell.value % 1 != 0.0
                    values.append(
                        unicode(cell.value)
                        if is_float
                        else unicode(int(cell.value))
                    )
                elif cell.ctype is xlrd.XL_CELL_DATE:
                    is_datetime = cell.value % 1 != 0.0
                    # emulate xldate_as_datetime for pre-0.9.3
                    dt = datetime.datetime(*xlrd.xldate.xldate_as_tuple(cell.value, book.datemode))
                    values.append(
                        dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                        if is_datetime
                        else dt.strftime(DEFAULT_SERVER_DATE_FORMAT)
                    )
                elif cell.ctype is xlrd.XL_CELL_BOOLEAN:
                    values.append(u'True' if cell.value else u'False')
                elif cell.ctype is xlrd.XL_CELL_ERROR:
                    raise ValueError(
                        _("Error cell found while reading XLS/XLSX file: %s") %
                        xlrd.error_text_from_code.get(
                            cell.value, "unknown error code %s" % cell.value)
                    )
                else:
                    values.append(cell.value)
            if any(x for x in values if x.strip()):
                yield values

    # use the same method for xlsx and xls files
    _read_xlsx = _read_xls

    @api.multi
    def _read_ods(self, options):
        """ Read file content using ODSReader custom lib """
        doc = odf_ods_reader.ODSReader(file=io.BytesIO(self.file))

        return (
            row
            for row in doc.getFirstSheet()
            if any(x for x in row if x.strip())
        )

    @api.multi
    def _read_csv(self, options):
        """ Returns a CSV-parsed iterator of all empty lines in the file
            :throws csv.Error: if an error is detected during CSV parsing
            :throws UnicodeDecodeError: if ``options.encoding`` is incorrect
        """
        csv_data = self.file

        # TODO: guess encoding with chardet? Or https://github.com/aadsm/jschardet
        encoding = options.get('encoding', 'utf-8')
        if encoding != 'utf-8':
            # csv module expect utf-8, see http://docs.python.org/2/library/csv.html
            csv_data = csv_data.decode(encoding).encode('utf-8')

        csv_iterator = csv.reader(
            StringIO(csv_data),
            quotechar=str(options['quoting']),
            delimiter=str(options['separator']))

        return (
            [item.decode('utf-8') for item in row]
            for row in csv_iterator
            if any(x for x in row if x.strip())
        )

    @api.model
    def _try_match_column(self, preview_values, options):
        """ Returns the potential field types, based on the preview values, using heuristics
            :param preview_values : list of value for the column to determine
            :param options : parsing options
        """
        # If all values are empty in preview than can be any field
        if all([v == '' for v in preview_values]):
            return ['all']
        # If all values starts with __export__ this is probably an id
        if all(v.startswith('__export__') for v in preview_values):
            return ['id', 'many2many', 'many2one', 'one2many']
        # If all values can be cast to int type is either id, float or monetary
        # Exception: if we only have 1 and 0, it can also be a boolean
        try:
            field_type = ['id', 'integer', 'float', 'monetary', 'many2one', 'many2many', 'one2many']
            res = set(int(v) for v in preview_values)
            if {0, 1}.issuperset(res):
                field_type.append('boolean')
            return field_type
        except ValueError:
            pass
        # If all values are either True or False, type is boolean
        if all(val.lower() in ('true', 'false', 't', 'f', '') for val in preview_values):
            return ['boolean']
        # If all values can be cast to float, type is either float or monetary
        try:
            thousand_separator = decimal_separator = False
            for val in preview_values:
                if val == '':
                    continue
                # value might have the currency symbol left or right from the value
                val = self._remove_currency_symbol(val)
                if val:
                    if options.get('float_thousand_separator') and options.get('float_decimal_separator'):
                        val = val.replace(options['float_thousand_separator'], '').replace(options['float_decimal_separator'], '.')
                    # We are now sure that this is a float, but we still need to find the
                    # thousand and decimal separator
                    else:
                        if val.count('.') > 1:
                            options['float_thousand_separator'] = '.'
                            options['float_decimal_separator'] = ','
                        elif val.count(',') > 1:
                            options['float_thousand_separator'] = ','
                            options['float_decimal_separator'] = '.'
                        elif val.find('.') > val.find(','):
                            thousand_separator = ','
                            decimal_separator = '.'
                        elif val.find(',') > val.find('.'):
                            thousand_separator = '.'
                            decimal_separator = ','
                else:
                    # This is not a float so exit this try
                    float('a')
            if thousand_separator and not options.get('float_decimal_separator'):
                options['float_thousand_separator'] = thousand_separator
                options['float_decimal_separator'] = decimal_separator
            return ['float', 'monetary']
        except ValueError:
            pass
        # Try to see if all values are a date or datetime
        dt = datetime.datetime
        separator = [' ', '/', '-']
        date_format = ['%mr%dr%Y', '%dr%mr%Y', '%Yr%mr%d', '%Yr%dr%m']
        date_patterns = [options['date_format']] if options.get('date_format') else []
        if not date_patterns:
            date_patterns = [pattern.replace('r', sep) for sep in separator for pattern in date_format]
            date_patterns.extend([p.replace('Y', 'y') for p in date_patterns])
        datetime_patterns = [options['datetime_format']] if options.get('datetime_format') else []
        if not datetime_patterns:
            datetime_patterns = [pattern + ' %H:%M:%S' for pattern in date_patterns]

        current_date_pattern = False
        current_datetime_pattern = False

        def check_patterns(patterns, preview_values):
            for pattern in patterns:
                match = True
                for val in preview_values:
                    if not val:
                        continue
                    try:
                        dt.strptime(val, pattern)
                    except ValueError:
                        match = False
                        break
                if match:
                    return pattern
            return False

        current_date_pattern = check_patterns(date_patterns, preview_values)
        if current_date_pattern:
            options['date_format'] = current_date_pattern
            return ['date']

        current_datetime_pattern = check_patterns(datetime_patterns, preview_values)
        if current_datetime_pattern:
            options['datetime_format'] = current_datetime_pattern
            return ['datetime']

        return ['text', 'char', 'datetime', 'selection', 'many2one', 'one2many', 'many2many', 'html']

    @api.model
    def _find_type_from_preview(self, options, preview):
        type_fields = []
        if preview:
            for column in range(0, len(preview[0])):
                preview_values = [value[column].strip() for value in preview]
                type_field = self._try_match_column(preview_values, options)
                type_fields.append(type_field)
        return type_fields

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
        string_match = None
        for field in fields:
            # FIXME: should match all translations & original
            # TODO: use string distance (levenshtein? hamming?)
            if header.lower() == field['name'].lower():
                return [field]
            if header.lower() == field['string'].lower():
                # matching string are not reliable way because
                # strings have no unique constraint
                string_match = field
        if string_match:
            # this behavior is only applied if there is no matching field['name']
            return [string_match]

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
            if not match:
                return []
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

            Returns a pair of (None, None) if headers were not requested
            or the list of headers and a dict mapping cell indices
            to key paths in the ``fields`` tree

            :param Iterator rows:
            :param dict fields:
            :param dict options:
            :rtype: (None, None) | (list(str), dict(int: list(str)))
        """
        if not options.get('headers'):
            return None, None

        headers = next(rows)
        return headers, {
            index: [field['name'] for field in self._match_header(header, fields, options)] or None
            for index, header in enumerate(headers)
        }

    @api.multi
    def parse_preview(self, options, count=10):
        """ Generates a preview of the uploaded files, and performs
            fields-matching between the import's file data and the model's
            columns.

            If the headers are not requested (not options.headers),
            ``matches`` and ``headers`` are both ``False``.

            :param int count: number of preview lines to generate
            :param options: format-specific options.
                            CSV: {encoding, quoting, separator, headers}
            :type options: {str, str, str, bool}
            :returns: {fields, matches, headers, preview} | {error, preview}
            :rtype: {dict(str: dict(...)), dict(int, list(str)), list(str), list(list(str))} | {str, str}
        """
        self.ensure_one()
        fields = self.get_fields(self.res_model)
        try:
            rows = self._read_file(options)
            headers, matches = self._match_headers(rows, fields, options)
            # Match should have consumed the first row (iif headers), get
            # the ``count`` next rows for preview
            preview = list(itertools.islice(rows, count))
            assert preview, "CSV file seems to have no content"
            header_types = self._find_type_from_preview(options, preview)
            if options.get('keep_matches', False) and len(options.get('fields', [])):
                matches = {}
                for index, match in enumerate(options.get('fields')):
                    if match:
                        matches[index] = match.split('/')

            return {
                'fields': fields,
                'matches': matches or False,
                'headers': headers or False,
                'headers_type': header_types or False,
                'preview': preview,
                'options': options,
                'advanced_mode': any([len(models.fix_import_export_id_paths(col)) > 1 for col in headers]),
                'debug': self.user_has_groups('base.group_no_one'),
            }
        except Exception as error:
            # Due to lazy generators, UnicodeDecodeError (for
            # instance) may only be raised when serializing the
            # preview to a list in the return.
            _logger.debug("Error during parsing preview", exc_info=True)
            preview = None
            if self.file_type == 'text/csv':
                preview = self.file[:ERROR_PREVIEW_BYTES].decode('iso-8859-1')
            return {
                'error': str(error),
                # iso-8859-1 ensures decoding will always succeed,
                # even if it yields non-printable characters. This is
                # in case of UnicodeDecodeError (or csv.Error
                # compounded with UnicodeDecodeError)
                'preview': preview,
            }

    @api.model
    def _convert_import_data(self, fields, options):
        """ Extracts the input BaseModel and fields list (with
            ``False``-y placeholders for fields to *not* import) into a
            format Model.import_data can use: a fields list without holes
            and the precisely matching data matrix

            :param list(str|bool): fields
            :returns: (data, fields)
            :rtype: (list(list(str)), list(str))
            :raises ValueError: in case the import data could not be converted
        """
        # Get indices for non-empty fields
        indices = [index for index, field in enumerate(fields) if field]
        if not indices:
            raise ValueError(_("You must configure at least one field to import"))
        # If only one index, itemgetter will return an atom rather
        # than a 1-tuple
        if len(indices) == 1:
            mapper = lambda row: [row[indices[0]]]
        else:
            mapper = operator.itemgetter(*indices)
        # Get only list of actually imported fields
        import_fields = [f for f in fields if f]

        rows_to_import = self._read_file(options)
        if options.get('headers'):
            rows_to_import = itertools.islice(rows_to_import, 1, None)
        data = [
            list(row) for row in pycompat.imap(mapper, rows_to_import)
            # don't try inserting completely empty rows (e.g. from
            # filtering out o2m fields)
            if any(row)
        ]

        return data, import_fields

    @api.model
    def _remove_currency_symbol(self, value):
        value = value.strip()
        negative = False
        # Careful that some countries use () for negative so replace it by - sign
        if value.startswith('(') and value.endswith(')'):
            value = value[1:-1]
            negative = True
        float_regex = re.compile(r'([-]?[0-9.,]+)')
        split_value = [g for g in float_regex.split(value) if g]
        if len(split_value) > 2:
            # This is probably not a float
            return False
        if len(split_value) == 1:
            if float_regex.search(split_value[0]) is not None:
                return split_value[0] if not negative else '-' + split_value[0]
            return False
        else:
            # String has been split in 2, locate which index contains the float and which does not
            currency_index = 0
            if float_regex.search(split_value[0]) is not None:
                currency_index = 1
            # Check that currency exists
            currency = self.env['res.currency'].search([('symbol', '=', split_value[currency_index].strip())])
            if len(currency):
                return split_value[currency_index + 1 % 2] if not negative else '-' + split_value[currency_index + 1 % 2]
            # Otherwise it is not a float with a currency symbol
            return False

    @api.model
    def _parse_float_from_data(self, data, index, name, options):
        thousand_separator = options.get('float_thousand_separator', ' ')
        decimal_separator = options.get('float_decimal_separator', '.')
        for line in data:
            if not line[index]:
                continue
            line[index] = line[index].replace(thousand_separator, '').replace(decimal_separator, '.')
            old_value = line[index]
            line[index] = self._remove_currency_symbol(line[index])
            if line[index] is False:
                raise ValueError(_("Column %s contains incorrect values (value: %s)" % (name, old_value)))

    @api.multi
    def _parse_import_data(self, data, import_fields, options):
        # Get fields of type date/datetime
        all_fields = self.env[self.res_model].fields_get()
        for name, field in pycompat.items(all_fields):
            if field['type'] in ('date', 'datetime') and name in import_fields:
                # Parse date
                index = import_fields.index(name)
                dt = datetime.datetime
                server_format = DEFAULT_SERVER_DATE_FORMAT if field['type'] == 'date' else DEFAULT_SERVER_DATETIME_FORMAT

                if options.get('%s_format' % field['type'], server_format) != server_format:
                    user_format = ustr(options.get('%s_format' % field['type'])).encode('utf-8')
                    for num, line in enumerate(data):
                        if line[index]:
                            try:
                                line[index] = dt.strftime(dt.strptime(ustr(line[index]).encode('utf-8'), user_format), server_format)
                            except ValueError as e:
                                raise ValueError(_("Column %s contains incorrect values. Error in line %d: %s") % (name, num + 1, e))
                            except Exception as e:
                                raise ValueError(_("Error Parsing Date [%s:L%d]: %s") % (name, num + 1, e))

            elif field['type'] in ('float', 'monetary') and name in import_fields:
                # Parse float, sometimes float values from file have currency symbol or () to denote a negative value
                # We should be able to manage both case
                index = import_fields.index(name)
                self._parse_float_from_data(data, index, name, options)
        return data

    @api.multi
    def do(self, fields, options, dryrun=False):
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
        self.ensure_one()
        self._cr.execute('SAVEPOINT import')

        try:
            data, import_fields = self._convert_import_data(fields, options)
            # Parse date and float field
            data = self._parse_import_data(data, import_fields, options)
        except ValueError as error:
            return [{
                'type': 'error',
                'message': unicode(error),
                'record': False,
            }]

        _logger.info('importing %d rows...', len(data))
        import_result = self.env[self.res_model].with_context(import_file=True).load(import_fields, data)
        _logger.info('done')

        # If transaction aborted, RELEASE SAVEPOINT is going to raise
        # an InternalError (ROLLBACK should work, maybe). Ignore that.
        # TODO: to handle multiple errors, create savepoint around
        #       write and release it in case of write error (after
        #       adding error to errors array) => can keep on trying to
        #       import stuff, and rollback at the end if there is any
        #       error in the results.
        try:
            if dryrun:
                self._cr.execute('ROLLBACK TO SAVEPOINT import')
            else:
                self._cr.execute('RELEASE SAVEPOINT import')
        except psycopg2.InternalError:
            pass

        return import_result['messages']
