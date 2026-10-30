import io
from datetime import datetime
from typing import TYPE_CHECKING

import xlsxwriter
from PIL import ImageFont

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import file_path, float_repr, format_date, formatLang, parse_version

if TYPE_CHECKING:
    from .pos_report_handler import PosReportHandler


class PosReport(models.Model):
    _name = 'pos.report'
    _description = 'POS Report'

    name = fields.Char(required=True)
    handler_model_id = fields.Many2one('ir.model', string='Handler Model')
    handler_model_name = fields.Char(related='handler_model_id.model', string='Handler Model Name')

    def _get_handler(self) -> "PosReportHandler":
        self.ensure_one()
        if not self.handler_model_name:
            raise UserError(_("No report handler configured for '%s'.", self.name))
        return self.env[self.handler_model_name]

    @api.model
    def get_report_info(self, report_id):
        report = self.browse(report_id)
        handler = report._get_handler()
        return {
            'id': report.id,
            'name': report.name,
            'handler': report.handler_model_name,
            'filters': handler._get_filters(),
        }

    @api.model
    def get_report_data(self, report_id):
        report = self.browse(report_id)
        handler = report._get_handler()
        currency = handler._get_currency()
        return {
            'report_name': handler._get_report_name(report.name),
            'sections': handler._get_sections_data(),
            'currency': {
                'id': currency.id,
                'symbol': currency.symbol,
                'position': currency.position,
                'decimal_places': currency.decimal_places,
            },
        }

    @api.model
    def get_unfold_data(self, report_id):
        """Return children lines for a given section / record combination."""
        report = self.browse(report_id)
        handler = report._get_handler()

        return {
            'section_id': self.env.context.get('section_id'),
            'lines': handler._get_unfold_lines(self.env.context.get('section_id')),
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
                col_id: self._format_value(value, col_types[col_id], currency)
                if col_id in col_types else value
                for col_id, value in line_values.items()
            }

            self._format_tree_values(node.get('lines') or [], currency, node_columns)

    def _format_value(self, value, col_type, currency=None):
        """Format a value to display according to its column type."""
        if value is None:
            return ''

        if col_type == 'monetary':
            return formatLang(self.env, value, currency_obj=currency)

        if col_type == 'integer':
            return formatLang(self.env, int(value), digits=0)

        if col_type == 'float':
            return formatLang(self.env, value, digits=currency.decimal_places)

        if col_type == 'percentage':
            return f"{formatLang(self.env, value, digits=2)}%"

        return str(value)

    def _get_filter_descriptions(self):
        """Build readable filter descriptions from context."""
        ctx = self.env.context
        descriptions = []

        if ctx.get('date_from'):
            descriptions.append({
                'label': _('Start Date'),
                'value': ctx['date_from'],
            })
        if ctx.get('date_to'):
            descriptions.append({
                'label': _('End Date'),
                'value': ctx['date_to'],
            })

        config_ids = ctx.get('config_ids', [])
        if config_ids:
            configs = self.env['pos.config'].browse(config_ids)
            descriptions.append({
                'label': _('Points of Sale'),
                'value': ', '.join(configs.mapped('name')),
            })

        session_id = ctx.get('session_id')
        if session_id:
            session = self.env['pos.session'].browse(session_id)
            descriptions.append({
                'label': _('Session'),
                'value': session.name,
            })

        return descriptions

    def _get_export_context(self):
        handler = self._get_handler().with_context(unfold_all=True)
        currency = handler._get_currency()

        sections = handler._get_sections_data()
        self._format_tree_values(sections, currency)

        return [{
            'company': self.env.company,
            'report_name': handler._get_report_name(self.name),
            'generation_date': format_date(self.env, datetime.now()),
            'filters': self._get_filter_descriptions(),
            'sections': sections,
            'currency': currency,
            'pdf_templates': handler._get_pdf_templates(),
        }]

    def export_to_pdf(self):
        """Generate the POS report as a PDF using the handler-generated report data."""
        self.ensure_one()

        action_report = self.env['ir.actions.report']
        report_contexts = self._get_export_context()

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
        return export_context.get('report_name')[:31]

    def _write_xlsx_extra_header(self, sheet, export_context, row, write_cell, formats):
        """Hook to write extra content above the report sections. Return the next free row."""
        return row

    def _write_xlsx_worksheet(self, workbook, sheet, export_context):
        """Populate a single worksheet from one export context."""
        currency = export_context['currency']
        filter_descriptions = export_context['filters']
        sections_data = export_context['sections']
        handler = self._get_handler()

        fonts = self._get_xlsx_export_fonts()

        def write_cell(col, row, value, fmt):
            self._set_xlsx_cell_sizes(sheet, fonts, col, row, value, fmt, False)
            sheet.write(row, col, value, fmt)

        base_props = {'font_name': 'Lato', 'font_size': 11, 'font_color': '#333333'}
        fmt_filter_title = workbook.add_format({**base_props, 'bold': True, 'font_size': 12})
        fmt_filter_label = workbook.add_format({**base_props, 'bold': True})
        fmt_filter_value = workbook.add_format(base_props)
        fmt_section_title = workbook.add_format({**base_props, 'bold': True, 'font_size': 13, 'bottom': 6, 'bg_color': '#c5c5c5'})
        fmt_col_header = workbook.add_format({**base_props, 'bold': True, 'bottom': 1, 'align': 'right'})
        fmt_col_header_left = workbook.add_format({**base_props, 'bold': True, 'bottom': 1, 'align': 'left'})

        # Format caches to avoid duplicate XlsxWriter Format objects.
        data_fmt_cache = {}
        name_fmt_cache = {}

        def _num_format(col_type):
            return {'monetary': '#,##0.00', 'float': '#,##0.00', 'integer': '0', 'percentage': '0.00%'}.get(col_type)

        def get_data_fmt(col_type, bold=False, indent=0):
            key = (col_type, bold, indent)
            if key not in data_fmt_cache:
                props = {**base_props, 'bold': bold}
                nf = _num_format(col_type)
                if nf:
                    props['num_format'] = nf
                props['align'] = 'left' if not nf else 'right'
                if indent:
                    props['indent'] = indent
                data_fmt_cache[key] = workbook.add_format(props)
            return data_fmt_cache[key]

        def get_name_fmt(bold=False, indent=0):
            key = (bold, indent)
            if key not in name_fmt_cache:
                props = {**base_props, 'bold': bold, 'align': 'left'}
                if indent:
                    props['indent'] = indent
                name_fmt_cache[key] = workbook.add_format(props)
            return name_fmt_cache[key]

        # Write filters at the top of the sheet.
        row = 0
        write_cell(0, row, _('Filters:'), fmt_filter_title)
        row += 1
        for desc in filter_descriptions:
            write_cell(0, row, str(desc.get('label', '')), fmt_filter_label)
            write_cell(1, row, str(desc.get('value', '')), fmt_filter_value)
            row += 1
        if not filter_descriptions:
            write_cell(0, row, _('No active filters'), fmt_filter_value)
            row += 1
        row += 1  # blank row before data

        row = self._write_xlsx_extra_header(sheet, export_context, row, write_cell, {
            'title': fmt_section_title,
            'label': fmt_filter_label,
            'value': fmt_filter_value,
            'col_header': fmt_col_header,
            'col_header_left': fmt_col_header_left,
            'integer': get_data_fmt('integer'),
            'monetary': get_data_fmt('monetary'),
        })

        for section in sections_data:
            columns = handler._get_xlsx_section_columns(section)
            section_name = section.get('name') or section.get('section_id', '')

            # Section title row merged across all columns.
            total_cols = 1 + len(columns)
            sheet.set_row(row, height=18)
            if total_cols > 1:
                sheet.merge_range(row, 0, row, total_cols - 1, section_name, fmt_section_title)
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
            row += 1

            def write_lines(lines, depth=0):
                nonlocal row
                for line in lines:
                    is_bold = line.get('style') == 'bold'
                    write_cell(0, row, line.get('name') or '', get_name_fmt(bold=is_bold, indent=depth))
                    for col_idx, col_def in enumerate(columns, start=1):
                        raw = handler._get_xlsx_row_value(line, col_def)
                        if raw is None:
                            sheet.write(row, col_idx, '', get_data_fmt('string', bold=is_bold))
                        else:
                            write_cell(col_idx, row, raw, get_data_fmt(col_def.get('type', 'string'), bold=is_bold))
                    row += 1
                    if line.get('lines'):
                        write_lines(line['lines'], depth=depth + 1)

            write_lines(section.get('lines') or [])
            row += 1  # blank row between sections

        # Ensure name column (col 0) is at least 30 units wide.
        if parse_version(xlsxwriter.__version__) >= parse_version('3.0.6'):
            current = sheet.col_info.get(0, [8.43])[0]
        else:
            current = sheet.col_sizes.get(0, [8.43])[0]

        if current < 30:
            sheet.set_column(0, 0, 30)

    def export_to_xlsx(self):
        """Generate the POS report as an XLSX file."""
        self.ensure_one()

        export_contexts = self._get_export_context()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True, 'strings_to_formulas': False})

        for export_context in export_contexts:
            sheet = workbook.add_worksheet(self._get_xlsx_sheet_name(export_context))
            self._write_xlsx_worksheet(workbook, sheet, export_context)

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()

        return {
            'file_name': f"{self.name}.xlsx",
            'file_content': generated_file,
            'file_type': 'xlsx',
        }
