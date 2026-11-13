import io
from datetime import datetime
from typing import TYPE_CHECKING

import xlsxwriter
from PIL import ImageFont

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import (
    file_path,
    float_repr,
    float_round,
    format_date,
    formatLang,
    parse_version,
)

if TYPE_CHECKING:
    from .pos_report_handler import PosReportHandler


class PosReport(models.Model):
    _name = 'pos.report'
    _description = 'POS Report'

    name = fields.Char(required=True)
    handler_model_id = fields.Many2one('ir.model', string='Handler Model', index='btree')
    handler_model_name = fields.Char(related='handler_model_id.model', string='Handler Model Name')

    def _get_handler(self) -> "PosReportHandler":
        self.ensure_one()
        if not self.handler_model_name:
            raise UserError(_("No report handler configured for '%s'.", self.name))
        return self.env[self.handler_model_name]

    def get_report_info(self):
        self.ensure_one()
        handler = self._get_handler()
        return {
            'id': self.id,
            'name': self.name,
            'handler': self.handler_model_name,
            'filters': handler._get_filters(),
        }

    def get_report_data(self, options):
        self.ensure_one()
        handler = self._get_handler()
        currency = handler._get_currency(options)
        data = {
            'report_name': handler._get_report_name(options) or self.name,
            'sections': handler._get_sections_data(options),
            'currency': {
                'id': currency.id,
                'symbol': currency.symbol,
                'position': currency.position,
                'decimal_places': currency.decimal_places,
            },
        }
        extension_data = handler._get_extension_data(options)
        if extension_data:
            data['extension_data'] = extension_data
        return data

    def get_unfold_data(self, options, section_id):
        """Return children lines for a given section / record combination."""
        self.ensure_one()
        handler = self._get_handler()

        return {
            'section_id': section_id,
            'lines': handler._get_unfold_lines(options, section_id),
        }

    def _format_tree_values(self, nodes, currency, columns=[]):
        """Format report values recursively while preserving non-column values."""
        for node in nodes:
            node_columns = node.get('columns') or columns
            col_types = {
                col.get('id'): col.get('type', 'string')
                for col in node_columns if col.get('id')
            }

            line_values = node.get('values') or {}
            node['values'] = {
                col_id: self._format_value(value, col_types[col_id], line=node, currency=currency)
                if col_id in col_types else value
                for col_id, value in line_values.items()
            }

            self._format_tree_values(node.get('lines') or [], currency, node_columns)

    def _format_value(self, value, col_type, line=None, currency=None):
        """Format a value to display according to its column type."""
        if value is None:
            return ''

        if col_type == 'monetary':
            return formatLang(self.env, value, currency_obj=currency)

        if col_type == 'integer':
            return formatLang(self.env, int(value), digits=0)

        if col_type == 'quantity':
            digits = self.env['decimal.precision'].precision_get('Product Unit')
            quantity = str(float_round(float(value), precision_digits=digits))
            values = (line or {}).get('values') or {}
            if values.get('uom'):
                return f"{quantity} {values['uom']}"
            return quantity

        if col_type == 'float':
            return formatLang(self.env, value, digits=currency.decimal_places)

        if col_type == 'percentage':
            return f"{formatLang(self.env, value, digits=2)}%"

        return str(value)

    def _get_export_context(self, options):
        handler = self._get_handler()
        options = {**options, 'unfold_all': True}
        currency = handler._get_currency(options)

        sections = handler._get_sections_data(options)
        self._format_tree_values(sections, currency)

        export_context = {
            'company': self.env.company,
            'report_name': handler._get_report_name(options) or self.name,
            'generation_date': format_date(self.env, datetime.now()),
            'filters': handler._get_filter_descriptions(options),
            'sections': sections,
            'currency': currency,
            'pdf_templates': handler._get_pdf_templates(),
        }
        return handler._get_export_context(self, options, export_context)

    def _export_to_pdf(self, options):
        """Generate the POS report as a PDF using the handler-generated report data."""
        self.ensure_one()

        action_report = self.env['ir.actions.report']
        report_contexts = self._get_export_context(options)

        html = action_report._render_template(
            'point_of_sale.pos_report_pdf_main',
            {'report_contexts': report_contexts},
        ).decode()

        pdf_bytes = action_report._run_pdf_engine_without_processing(
            'wkhtmltopdf',
            [html],
            report_ref=False,
            header=None,
            footer=None,
            landscape=False,
            specific_paperformat_args={
                'data-report-margin-top': 10,
                'data-report-header-spacing': 10,
                'data-report-margin-bottom': 15,
            },
        )

        return {
            'file_name': f"{self.name}.pdf",
            'file_content': pdf_bytes,
            'file_type': 'pdf',
        }

    def _get_xlsx_export_fonts(self):
        """Get Lato font variants for column-width measurement."""
        fonts = {}
        for font_type in ('Reg', 'Bol', 'RegIta', 'BolIta'):
            try:
                lato_path = f'web/static/fonts/lato/Lato-{font_type}-webfont.ttf'
                fonts[font_type] = ImageFont.truetype(file_path(lato_path), 12)
            except (OSError, FileNotFoundError):
                fonts[font_type] = ImageFont.load_default()
        return fonts

    def _set_xlsx_cell_sizes(self, sheet, fonts, col, row, value, style, has_colspan):
        """Resize column when cell content is wider than the current width (max 75)."""
        def get_string_width(font, string):
            return font.getlength(string) / 5

        font_type = ('Bol' if style.bold else 'Reg') + ('Ita' if style.italic else '')
        report_font = fonts[font_type]

        if parse_version(xlsxwriter.__version__) >= parse_version('3.0.6'):
            try:
                col_width = sheet.col_info[col][0]
            except KeyError:
                col_width = 8.43
        else:
            col_width = sheet.col_sizes.get(col, [8.43])[0]

        if value is None:
            value = ''
        else:
            try:
                value = float_repr(float(value), self.env.company.currency_id.decimal_places)
            except (ValueError, OverflowError):
                pass

        if not has_colspan:
            indent = style.indent or 0
            formatted_value = f"{'  ' * indent}{value}"
            width = get_string_width(
                report_font,
                max(formatted_value.split('\n'), key=lambda line: get_string_width(report_font, line)),
            )
            if width > col_width:
                sheet.set_column(col, col, min(width + 4, 75))

    def _get_xlsx_sheet_name(self, export_context):
        return export_context.get('xlsx_sheet_name') or export_context.get('report_name')[:31]

    def _add_options_xlsx_sheet(self, workbook, export_contexts):
        """Summarize the applied filters for each exported report."""
        sheet = workbook.add_worksheet(_('Filters'))
        sheet.set_column(0, 0, 30)
        sheet.set_column(1, 1, 50)
        label_format = workbook.add_format({'font_name': 'Lato', 'bold': True})
        value_format = workbook.add_format({'font_name': 'Lato', 'text_wrap': True})
        row = 0
        for export_context in export_contexts:
            if len(export_contexts) > 1:
                sheet.write(row, 0, self._get_xlsx_sheet_name(export_context), label_format)
                row += 1
            for description in export_context['filters']:
                sheet.write(row, 0, description['label'], label_format)
                sheet.write(row, 1, description['value'], value_format)
                row += 1
            if not export_context['filters']:
                sheet.write(row, 0, _('No active filters'), value_format)
                row += 1
            row += 1

    def _write_xlsx_worksheet(self, workbook, sheet, export_context):
        """Populate a single worksheet from one export context."""
        currency = export_context['currency']
        sections_data = export_context['sections']
        handler = self._get_handler()

        fonts = self._get_xlsx_export_fonts()

        def write_cell(col, row, value, fmt):
            self._set_xlsx_cell_sizes(sheet, fonts, col, row, value, fmt, False)
            sheet.write(row, col, value, fmt)

        base_props = {'font_name': 'Lato', 'font_size': 11, 'font_color': '#333333'}
        fmt_filter_label = workbook.add_format({**base_props, 'bold': True})
        fmt_filter_value = workbook.add_format(base_props)
        fmt_section_title = workbook.add_format({**base_props, 'bold': True, 'font_size': 13, 'bottom': 6, 'bg_color': '#c5c5c5'})
        fmt_col_header = workbook.add_format({**base_props, 'bold': True, 'bottom': 1, 'bg_color': '#e9ecef', 'align': 'right'})
        fmt_col_header_left = workbook.add_format({**base_props, 'bold': True, 'bottom': 1, 'bg_color': '#e9ecef', 'align': 'left'})

        # Format caches to avoid duplicate XlsxWriter Format objects.
        data_fmt_cache = {}
        name_fmt_cache = {}

        def _num_format(col_type):
            return {'monetary': '#,##0.00', 'float': '#,##0.00', 'integer': '0', 'percentage': '0.00%'}.get(col_type)

        def get_row_props(bold, depth):
            if depth == 0:
                return {'bold': True, 'bg_color': '#e9ecef', 'bottom': 6}
            if bold:
                return {'bold': True, 'bottom': 1}
            return {'bold': False}

        def get_data_fmt(col_type, bold=False, indent=0, depth=None):
            key = (col_type, bold, indent, depth)
            if key not in data_fmt_cache:
                props = {**base_props, **get_row_props(bold, depth)}
                nf = _num_format(col_type)
                if nf:
                    props['num_format'] = nf
                props['align'] = 'right'
                if indent:
                    props['indent'] = indent
                data_fmt_cache[key] = workbook.add_format(props)
            return data_fmt_cache[key]

        def get_name_fmt(bold=False, indent=0):
            key = (bold, indent)
            if key not in name_fmt_cache:
                props = {**base_props, **get_row_props(bold, indent), 'align': 'left'}
                if indent:
                    props['indent'] = indent
                name_fmt_cache[key] = workbook.add_format(props)
            return name_fmt_cache[key]

        row = 0
        row = handler._write_xlsx_extra_header(sheet, export_context, row, write_cell, {
            'title': fmt_section_title,
            'label': fmt_filter_label,
            'value': fmt_filter_value,
            'col_header': fmt_col_header,
            'col_header_left': fmt_col_header_left,
            'integer': get_data_fmt('integer'),
            'monetary': get_data_fmt('monetary'),
        })

        section_columns = [handler._get_xlsx_section_columns(section) for section in sections_data]
        last_column = max((len(columns) for columns in section_columns), default=0)
        for section, columns in zip(sections_data, section_columns):

            # Keep the section title separate from its totals and detail rows.
            section_name = section.get('name') or section.get('section_id', '')
            sheet.set_row(row, 26)
            if last_column:
                sheet.merge_range(row, 0, row, last_column, section_name, fmt_section_title)
            else:
                write_cell(0, row, section_name, fmt_section_title)
            row += 1

            # Column header row.
            write_cell(0, row, _('Name'), fmt_col_header_left)
            for col_idx, col_def in enumerate(columns, start=1):
                col_label = col_def.get('label', '')
                if col_def.get('type') == 'monetary' and currency:
                    col_label = f"{col_label} ({currency.symbol})"
                write_cell(col_idx, row, col_label, fmt_col_header)
            for col_idx in range(len(columns) + 1, last_column + 1):
                sheet.write_blank(row, col_idx, None, fmt_col_header)
            row += 1

            def write_lines(lines, depth=0):
                nonlocal row
                for line in lines:
                    is_bold = depth == 0
                    if depth == 0:
                        sheet.set_row(row, 24)
                    write_cell(0, row, line.get('name') or '', get_name_fmt(bold=is_bold, indent=depth))
                    for col_idx, col_def in enumerate(columns, start=1):
                        raw = handler._get_xlsx_row_value(line, col_def)
                        if raw is None:
                            sheet.write(row, col_idx, '', get_data_fmt('string', bold=is_bold, depth=depth))
                        else:
                            write_cell(col_idx, row, raw, get_data_fmt(col_def.get('type', 'string'), bold=is_bold, depth=depth))
                    if depth == 0:
                        for col_idx in range(len(columns) + 1, last_column + 1):
                            sheet.write_blank(row, col_idx, None, get_data_fmt('string', bold=is_bold, depth=depth))
                    row += 1
                    if line.get('lines'):
                        write_lines(line['lines'], depth=depth + 1)

            write_lines([section])
            row += 1  # blank row between sections

        # Ensure name column (col 0) is at least 30 units wide.
        if parse_version(xlsxwriter.__version__) >= parse_version('3.0.6'):
            current = sheet.col_info.get(0, [8.43])[0]
        else:
            current = sheet.col_sizes.get(0, [8.43])[0]

        if current < 30:
            sheet.set_column(0, 0, 30)

    def _export_to_xlsx(self, options):
        """Generate the POS report as an XLSX file."""
        self.ensure_one()

        export_contexts = self._get_export_context(options)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True, 'strings_to_formulas': False})

        for export_context in export_contexts:
            sheet = workbook.add_worksheet(self._get_xlsx_sheet_name(export_context))
            self._write_xlsx_worksheet(workbook, sheet, export_context)

        self._add_options_xlsx_sheet(workbook, export_contexts)

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()

        return {
            'file_name': f"{self.name}.xlsx",
            'file_content': generated_file,
            'file_type': 'xlsx',
        }
