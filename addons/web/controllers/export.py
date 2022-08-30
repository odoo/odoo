# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import functools
import io
import itertools
import json
import logging
import operator
from collections import OrderedDict

from werkzeug.exceptions import InternalServerError

import odoo
import odoo.modules.registry
from odoo import http
from odoo.exceptions import UserError
from odoo.http import content_disposition, request
from odoo.tools import lazy_property, osutil, pycompat
from odoo.tools.misc import xlsxwriter
from odoo.tools.translate import _


_logger = logging.getLogger(__name__)


def none_values_filtered(func):
    @functools.wraps(func)
    def wrap(iterable):
        return func(v for v in iterable if v is not None)
    return wrap


def allow_empty_iterable(func):
    """
    Some functions do not accept empty iterables (e.g. max, min with no default value)
    This returns the function `func` such that it returns None if the iterable
    is empty instead of raising a ValueError.
    """
    @functools.wraps(func)
    def wrap(iterable):
        iterator = iter(iterable)
        try:
            value = next(iterator)
            return func(itertools.chain([value], iterator))
        except StopIteration:
            return None
    return wrap


OPERATOR_MAPPING = {
    'max': none_values_filtered(allow_empty_iterable(max)),
    'min': none_values_filtered(allow_empty_iterable(min)),
    'sum': sum,
    'bool_and': all,
    'bool_or': any,
}


class GroupsTreeNode:
    """
    This class builds an ordered tree of groups from the result of a `read_group(lazy=False)`.
    The `read_group` returns a list of dictionnaries and each dictionnary is used to
    build a leaf. The entire tree is built by inserting all leaves.
    """

    def __init__(self, model, fields, groupby, groupby_type, root=None):
        self._model = model
        self._export_field_names = fields  # exported field names (e.g. 'journal_id', 'account_id/name', ...)
        self._groupby = groupby
        self._groupby_type = groupby_type

        self.count = 0  # Total number of records in the subtree
        self.children = OrderedDict()
        self.data = []  # Only leaf nodes have data

        if root:
            self.insert_leaf(root)

    def _get_aggregate(self, field_name, data, group_operator):
        # When exporting one2many fields, multiple data lines might be exported for one record.
        # Blank cells of additionnal lines are filled with an empty string. This could lead to '' being
        # aggregated with an integer or float.
        data = (value for value in data if value != '')

        if group_operator == 'avg':
            return self._get_avg_aggregate(field_name, data)

        aggregate_func = OPERATOR_MAPPING.get(group_operator)
        if not aggregate_func:
            _logger.warning("Unsupported export of group_operator '%s' for field %s on model %s", group_operator, field_name, self._model._name)
            return

        if self.data:
            return aggregate_func(data)
        return aggregate_func((child.aggregated_values.get(field_name) for child in self.children.values()))

    def _get_avg_aggregate(self, field_name, data):
        aggregate_func = OPERATOR_MAPPING.get('sum')
        if self.data:
            return aggregate_func(data) / self.count
        children_sums = (child.aggregated_values.get(field_name) * child.count for child in self.children.values())
        return aggregate_func(children_sums) / self.count

    def _get_aggregated_field_names(self):
        """ Return field names of exported field having a group operator """
        aggregated_field_names = []
        for field_name in self._export_field_names:
            if field_name == '.id':
                field_name = 'id'
            if '/' in field_name:
                # Currently no support of aggregated value for nested record fields
                # e.g. line_ids/analytic_line_ids/amount
                continue
            field = self._model._fields[field_name]
            if field.group_operator:
                aggregated_field_names.append(field_name)
        return aggregated_field_names

    # Lazy property to memoize aggregated values of children nodes to avoid useless recomputations
    @lazy_property
    def aggregated_values(self):

        aggregated_values = {}

        # Transpose the data matrix to group all values of each field in one iterable
        field_values = zip(*self.data)
        for field_name in self._export_field_names:
            field_data = self.data and next(field_values) or []

            if field_name in self._get_aggregated_field_names():
                field = self._model._fields[field_name]
                aggregated_values[field_name] = self._get_aggregate(field_name, field_data, field.group_operator)

        return aggregated_values

    def child(self, key):
        """
        Return the child identified by `key`.
        If it doesn't exists inserts a default node and returns it.
        :param key: child key identifier (groupby value as returned by read_group,
                    usually (id, display_name))
        :return: the child node
        """
        if key not in self.children:
            self.children[key] = GroupsTreeNode(self._model, self._export_field_names, self._groupby, self._groupby_type)
        return self.children[key]

    def insert_leaf(self, group):
        """
        Build a leaf from `group` and insert it in the tree.
        :param group: dict as returned by `read_group(lazy=False)`
        """
        leaf_path = [group.get(groupby_field) for groupby_field in self._groupby]
        domain = group.pop('__domain')
        count = group.pop('__count')

        records = self._model.search(domain, offset=0, limit=False, order=False)

        # Follow the path from the top level group to the deepest
        # group which actually contains the records' data.
        node = self # root
        node.count += count
        for node_key in leaf_path:
            # Go down to the next node or create one if it does not exist yet.
            node = node.child(node_key)
            # Update count value and aggregated value.
            node.count += count

        node.data = records.export_data(self._export_field_names).get('datas', [])


class ExportXlsxWriter:

    def __init__(self, field_names, row_count=0):
        self.field_names = field_names
        self.output = io.BytesIO()
        self.workbook = xlsxwriter.Workbook(self.output, {'in_memory': True})
        self.base_style = self.workbook.add_format({'text_wrap': True})
        self.header_style = self.workbook.add_format({'bold': True})
        self.header_bold_style = self.workbook.add_format({'text_wrap': True, 'bold': True, 'bg_color': '#e9ecef'})
        self.date_style = self.workbook.add_format({'text_wrap': True, 'num_format': 'yyyy-mm-dd'})
        self.datetime_style = self.workbook.add_format({'text_wrap': True, 'num_format': 'yyyy-mm-dd hh:mm:ss'})
        self.worksheet = self.workbook.add_worksheet()
        self.value = False
        self.float_format = '#,##0.00'
        decimal_places = [res['decimal_places'] for res in
                          request.env['res.currency'].search_read([], ['decimal_places'])]
        self.monetary_format = f'#,##0.{max(decimal_places or [2]) * "0"}'

        if row_count > self.worksheet.xls_rowmax:
            raise UserError(_('There are too many rows (%s rows, limit: %s) to export as Excel 2007-2013 (.xlsx) format. Consider splitting the export.') % (row_count, self.worksheet.xls_rowmax))

    def __enter__(self):
        self.write_header()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    def write_header(self):
        # Write main header
        for i, fieldname in enumerate(self.field_names):
            self.write(0, i, fieldname, self.header_style)
        self.worksheet.set_column(0, max(0, len(self.field_names) - 1), 30) # around 220 pixels

    def close(self):
        self.workbook.close()
        with self.output:
            self.value = self.output.getvalue()

    def write(self, row, column, cell_value, style=None):
        self.worksheet.write(row, column, cell_value, style)

    def write_cell(self, row, column, cell_value):
        cell_style = self.base_style

        if isinstance(cell_value, bytes):
            try:
                # because xlsx uses raw export, we can get a bytes object
                # here. xlsxwriter does not support bytes values in Python 3 ->
                # assume this is base64 and decode to a string, if this
                # fails note that you can't export
                cell_value = pycompat.to_text(cell_value)
            except UnicodeDecodeError:
                raise UserError(_("Binary fields can not be exported to Excel unless their content is base64-encoded. That does not seem to be the case for %s.", self.field_names)[column])

        if isinstance(cell_value, str):
            if len(cell_value) > self.worksheet.xls_strmax:
                cell_value = _("The content of this cell is too long for an XLSX file (more than %s characters). Please use the CSV format for this export.", self.worksheet.xls_strmax)
            else:
                cell_value = cell_value.replace("\r", " ")
        elif isinstance(cell_value, datetime.datetime):
            cell_style = self.datetime_style
        elif isinstance(cell_value, datetime.date):
            cell_style = self.date_style
        elif isinstance(cell_value, float):
            cell_style.set_num_format(self.float_format)
        self.write(row, column, cell_value, cell_style)


class GroupExportXlsxWriter(ExportXlsxWriter):

    def __init__(self, fields, row_count=0):
        super().__init__([f['label'].strip() for f in fields], row_count)
        self.fields = fields

    def write_group(self, row, column, group_name, group, group_depth=0):
        group_name = group_name[1] if isinstance(group_name, tuple) and len(group_name) > 1 else group_name
        if group._groupby_type[group_depth] != 'boolean':
            group_name = group_name or _("Undefined")
        row, column = self._write_group_header(row, column, group_name, group, group_depth)

        # Recursively write sub-groups
        for child_group_name, child_group in group.children.items():
            row, column = self.write_group(row, column, child_group_name, child_group, group_depth + 1)

        for record in group.data:
            row, column = self._write_row(row, column, record)
        return row, column

    def _write_row(self, row, column, data):
        for value in data:
            self.write_cell(row, column, value)
            column += 1
        return row + 1, 0

    def _write_group_header(self, row, column, label, group, group_depth=0):
        aggregates = group.aggregated_values

        label = '%s%s (%s)' % ('    ' * group_depth, label, group.count)
        self.write(row, column, label, self.header_bold_style)
        for field in self.fields[1:]: # No aggregates allowed in the first column because of the group title
            column += 1
            aggregated_value = aggregates.get(field['name'])
            if field.get('type') == 'monetary':
                self.header_bold_style.set_num_format(self.monetary_format)
            elif field.get('type') == 'float':
                self.header_bold_style.set_num_format(self.float_format)
            else:
                aggregated_value = str(aggregated_value if aggregated_value is not None else '')
            self.write(row, column, aggregated_value, self.header_bold_style)
        return row + 1, 0


class Export(http.Controller):

    @http.route('/web/export/formats', type='json', auth="user")
    def formats(self):
        """ Returns all valid export formats

        :returns: for each export format, a pair of identifier and printable name
        :rtype: [(str, str)]
        """
        return [
            {'tag': 'xlsx', 'label': 'XLSX', 'error': None if xlsxwriter else "XlsxWriter 0.9.3 required"},
            {'tag': 'csv', 'label': 'CSV'},
        ]

    def fields_get(self, model):
        Model = request.env[model]
        fields = Model.fields_get()
        return fields

    @http.route('/web/export/get_fields', type='json', auth="user")
    def get_fields(self, model, prefix='', parent_name='',
                   import_compat=True, parent_field_type=None,
                   parent_field=None, exclude=None):

        fields = self.fields_get(model)
        if import_compat:
            if parent_field_type in ['many2one', 'many2many']:
                rec_name = request.env[model]._rec_name_fallback()
                fields = {'id': fields['id'], rec_name: fields[rec_name]}
        else:
            fields['.id'] = {**fields['id']}

        fields['id']['string'] = _('External ID')

        if parent_field:
            parent_field['string'] = _('External ID')
            fields['id'] = parent_field

        fields_sequence = sorted(fields.items(),
            key=lambda field: odoo.tools.ustr(field[1].get('string', '').lower()))

        records = []
        for field_name, field in fields_sequence:
            if import_compat and not field_name == 'id':
                if exclude and field_name in exclude:
                    continue
                if field.get('readonly'):
                    # If none of the field's states unsets readonly, skip the field
                    if all(dict(attrs).get('readonly', True)
                           for attrs in field.get('states', {}).values()):
                        continue
            if not field.get('exportable', True):
                continue

            ident = prefix + ('/' if prefix else '') + field_name
            val = ident
            if field_name == 'name' and import_compat and parent_field_type in ['many2one', 'many2many']:
                # Add name field when expand m2o and m2m fields in import-compatible mode
                val = prefix
            name = parent_name + (parent_name and '/' or '') + field['string']
            record = {'id': ident, 'string': name,
                      'value': val, 'children': False,
                      'field_type': field.get('type'),
                      'required': field.get('required'),
                      'relation_field': field.get('relation_field'),
                      'default_export': import_compat and field.get('default_export_compatible')}
            records.append(record)

            if len(ident.split('/')) < 3 and 'relation' in field:
                ref = field.pop('relation')
                record['value'] += '/id'
                record['params'] = {'model': ref, 'prefix': ident, 'name': name, 'parent_field': field}
                record['children'] = True

        return records

    @http.route('/web/export/namelist', type='json', auth="user")
    def namelist(self, model, export_id):
        # TODO: namelist really has no reason to be in Python (although itertools.groupby helps)
        export = request.env['ir.exports'].browse([export_id]).read()[0]
        export_fields_list = request.env['ir.exports.line'].browse(export['export_fields']).read()

        fields_data = self.fields_info(
            model, [f['name'] for f in export_fields_list])

        return [
            {'name': field['name'], 'label': fields_data[field['name']]}
            for field in export_fields_list
        ]

    def fields_info(self, model, export_fields):
        info = {}
        fields = self.fields_get(model)
        if ".id" in export_fields:
            fields['.id'] = fields.get('id', {'string': 'ID'})

        # To make fields retrieval more efficient, fetch all sub-fields of a
        # given field at the same time. Because the order in the export list is
        # arbitrary, this requires ordering all sub-fields of a given field
        # together so they can be fetched at the same time
        #
        # Works the following way:
        # * sort the list of fields to export, the default sorting order will
        #   put the field itself (if present, for xmlid) and all of its
        #   sub-fields right after it
        # * then, group on: the first field of the path (which is the same for
        #   a field and for its subfields and the length of splitting on the
        #   first '/', which basically means grouping the field on one side and
        #   all of the subfields on the other. This way, we have the field (for
        #   the xmlid) with length 1, and all of the subfields with the same
        #   base but a length "flag" of 2
        # * if we have a normal field (length 1), just add it to the info
        #   mapping (with its string) as-is
        # * otherwise, recursively call fields_info via graft_subfields.
        #   all graft_subfields does is take the result of fields_info (on the
        #   field's model) and prepend the current base (current field), which
        #   rebuilds the whole sub-tree for the field
        #
        # result: because we're not fetching the fields_get for half the
        # database models, fetching a namelist with a dozen fields (including
        # relational data) falls from ~6s to ~300ms (on the leads model).
        # export lists with no sub-fields (e.g. import_compatible lists with
        # no o2m) are even more efficient (from the same 6s to ~170ms, as
        # there's a single fields_get to execute)
        for (base, length), subfields in itertools.groupby(
                sorted(export_fields),
                lambda field: (field.split('/', 1)[0], len(field.split('/', 1)))):
            subfields = list(subfields)
            if length == 2:
                # subfields is a seq of $base/*rest, and not loaded yet
                info.update(self.graft_subfields(
                    fields[base]['relation'], base, fields[base]['string'],
                    subfields
                ))
            elif base in fields:
                info[base] = fields[base]['string']

        return info

    def graft_subfields(self, model, prefix, prefix_string, fields):
        export_fields = [field.split('/', 1)[1] for field in fields]
        return (
            (prefix + '/' + k, prefix_string + '/' + v)
            for k, v in self.fields_info(model, export_fields).items())


class ExportFormat(object):

    @property
    def content_type(self):
        """ Provides the format's content type """
        raise NotImplementedError()

    @property
    def extension(self):
        raise NotImplementedError()

    def filename(self, base):
        """ Creates a filename *without extension* for the item / format of
        model ``base``.
        """
        if base not in request.env:
            return base

        model_description = request.env['ir.model']._get(base).name
        return f"{model_description} ({base})"

    def from_data(self, fields, rows):
        """ Conversion method from Odoo's export data to whatever the
        current export class outputs

        :params list fields: a list of fields to export
        :params list rows: a list of records to export
        :returns:
        :rtype: bytes
        """
        raise NotImplementedError()

    def from_group_data(self, fields, groups):
        raise NotImplementedError()

    def base(self, data):
        params = json.loads(data)
        model, fields, ids, domain, import_compat = \
            operator.itemgetter('model', 'fields', 'ids', 'domain', 'import_compat')(params)

        Model = request.env[model].with_context(**params.get('context', {}))
        if not Model._is_an_ordinary_table():
            fields = [field for field in fields if field['name'] != 'id']

        field_names = [f['name'] for f in fields]
        if import_compat:
            columns_headers = field_names
        else:
            columns_headers = [val['label'].strip() for val in fields]

        groupby = params.get('groupby')
        if not import_compat and groupby:
            groupby_type = [Model._fields[x.split(':')[0]].type for x in groupby]
            domain = [('id', 'in', ids)] if ids else domain
            groups_data = Model.read_group(domain, [x if x != '.id' else 'id' for x in field_names], groupby, lazy=False)

            # read_group(lazy=False) returns a dict only for final groups (with actual data),
            # not for intermediary groups. The full group tree must be re-constructed.
            tree = GroupsTreeNode(Model, field_names, groupby, groupby_type)
            for leaf in groups_data:
                tree.insert_leaf(leaf)

            response_data = self.from_group_data(fields, tree)
        else:
            Model = Model.with_context(import_compat=import_compat)
            records = Model.browse(ids) if ids else Model.search(domain, offset=0, limit=False, order=False)

            export_data = records.export_data(field_names).get('datas', [])
            response_data = self.from_data(columns_headers, export_data)

        # TODO: call `clean_filename` directly in `content_disposition`?
        return request.make_response(response_data,
            headers=[('Content-Disposition',
                            content_disposition(
                                osutil.clean_filename(self.filename(model) + self.extension))),
                     ('Content-Type', self.content_type)],
        )

class CSVExport(ExportFormat, http.Controller):

    @http.route('/web/export/csv', type='http', auth="user")
    def index(self, data):
        try:
            return self.base(data)
        except Exception as exc:
            _logger.exception("Exception during request handling.")
            payload = json.dumps({
                'code': 200,
                'message': "Odoo Server Error",
                'data': http.serialize_exception(exc)
            })
            raise InternalServerError(payload) from exc

    @property
    def content_type(self):
        return 'text/csv;charset=utf8'

    @property
    def extension(self):
        return '.csv'

    def from_group_data(self, fields, groups):
        raise UserError(_("Exporting grouped data to csv is not supported."))

    def from_data(self, fields, rows):
        fp = io.BytesIO()
        writer = pycompat.csv_writer(fp, quoting=1)

        writer.writerow(fields)

        for data in rows:
            row = []
            for d in data:
                # Spreadsheet apps tend to detect formulas on leading =, + and -
                if isinstance(d, str) and d.startswith(('=', '-', '+')):
                    d = "'" + d

                row.append(pycompat.to_text(d))
            writer.writerow(row)

        return fp.getvalue()

class ExcelExport(ExportFormat, http.Controller):

    @http.route('/web/export/xlsx', type='http', auth="user")
    def index(self, data):
        try:
            return self.base(data)
        except Exception as exc:
            _logger.exception("Exception during request handling.")
            payload = json.dumps({
                'code': 200,
                'message': "Odoo Server Error",
                'data': http.serialize_exception(exc)
            })
            raise InternalServerError(payload) from exc

    @property
    def content_type(self):
        return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    @property
    def extension(self):
        return '.xlsx'

    def from_group_data(self, fields, groups):
        with GroupExportXlsxWriter(fields, groups.count) as xlsx_writer:
            x, y = 1, 0
            for group_name, group in groups.children.items():
                x, y = xlsx_writer.write_group(x, y, group_name, group)

        return xlsx_writer.value

    def from_data(self, fields, rows):
        with ExportXlsxWriter(fields, len(rows)) as xlsx_writer:
            for row_index, row in enumerate(rows):
                for cell_index, cell_value in enumerate(row):
                    if isinstance(cell_value, (list, tuple)):
                        cell_value = pycompat.to_text(cell_value)
                    xlsx_writer.write_cell(row_index + 1, cell_index, cell_value)

        return xlsx_writer.value
