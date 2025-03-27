
from odoo import http
from odoo.http import content_disposition, request
import io
import xlsxwriter
import json
 
class ReportController(http.Controller):
    @http.route([
        '/izi/excel/<int:block_id>',
    ], type='http', auth="user", csrf=False)
    def export_report(self, block_id, **kwargs):
        block = request.env['izi.dashboard.block'].browse(int(block_id))
        analysis = block.analysis_id
        if not analysis:
            return False
        name = analysis.name
        response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type', 'application/vnd.ms-excel'),
                        ('Content-Disposition', content_disposition('%s Report' % (name.title()) + '.xlsx'))
                    ]
                )
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
 
        title_style = workbook.add_format({'font_name': 'Arial', 'border': 0, 'font_size': 14, 'bold': True, 'align': 'left'})
        header_style = workbook.add_format({'font_name': 'Arial', 'border': 0, 'font_size': 10, 'bold': True, 'align': 'left'})
        text_style = workbook.add_format({'font_name': 'Arial', 'border': 0, 'font_size': 10, 'align': 'left', 'num_format': '@'})
        number_style = workbook.add_format({'font_name': 'Arial', 'border': 0, 'font_size': 10, 'align': 'right'})

        sheet = workbook.add_worksheet('Sheet 1')
        sheet.set_landscape()
        sheet.set_paper(9)
        sheet.set_margins(0.5,0.5,0.5,0.5)

        # sheet.write(0, 0, '%s REPORT %s TO %s' % (name.upper(), date_from, date_to), title_style)
        
        data = []
        data_kwargs = {}
        if kwargs.get('filters'):
            filters = json.loads(kwargs.get('filters'))
            data_kwargs['filters'] = filters
        if kwargs.get('allowed_company_ids'):
            data_kwargs['allowed_company_ids'] = json.loads(kwargs.get('allowed_company_ids'))
        result = analysis.get_analysis_data_dashboard(**data_kwargs)
        data = result.get('raw_data')
        fields = []
        if not fields and data and data[0].keys():
            fields = list(data[0].keys())
        
        replace_title = {
        }
        # Set Header
        i = 0
        while i < len(fields):
            field = fields[i]

            # Replace
            for key_replace_title in replace_title:
                if key_replace_title in field:
                    field = field.replace(key_replace_title, replace_title[key_replace_title])
            # field = field.replace('_', ' ') # .upper()

            # Write Header
            sheet.write(0, i, field, header_style)
            sheet.set_column(i, i, round(len(field)*1.5))
            i += 1

        row = 1
        for dt in data:
            col = 0
            for field in fields:
                cell_value = ''
                if field in dt and (dt[field] or dt[field] is 0):
                    cell_value = str(dt[field])
                sheet.write(row, col, cell_value, text_style)
                col += 1
            row += 1
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
 
        return response