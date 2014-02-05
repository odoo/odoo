from openerp import http
import simplejson
from openerp.http import request, serialize_exception as _serialize_exception
from cStringIO import StringIO

try:
    import xlwt
except ImportError:
    xlwt = None

class TableExporter(http.Controller):

    @http.route('/web_graph/check_xlwt', type='json', auth='none')
    def check_xlwt(self):
        return xlwt is not None


    @http.route('/web_graph/export_xls', type='http', auth="user")
    def export_xls(self, data, token):
        jdata = simplejson.loads(data)
        nbr_measures = jdata['nbr_measures']
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Sheet 1')
        bold_style = xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour gray25;")
        non_bold_style = xlwt.easyxf("pattern: pattern solid, fore_colour gray25;")
        bold = xlwt.easyxf("font: bold on;")

        # Step 1: writing headers
        headers = jdata['headers']
        x, y, L = 1, 0, []
        for i, header_row in enumerate(headers):
            worksheet.write(i,0, '', non_bold_style)
            for header in header_row:
                while (L and L[0]['x'] == x):
                    cell = L.pop(0)
                    for i in range(nbr_measures):
                        worksheet.write(y,x+i, '', non_bold_style)
                    if cell['height'] > 1:
                        L.append({'x': x, 'height':cell['height'] - 1})
                    x = x + nbr_measures
                style = non_bold_style if 'expanded' in header else bold_style
                for i in range(header['width']):
                    worksheet.write(y, x + i, header['title'] if i == 0 else '', style)
                if header['height'] > 1:
                    L.append({'x': x, 'height':header['height'] - 1})
                x = x + header['width'];
            while (L and L[0]['x'] == x):
                cell = L.pop(0)
                for i in range(nbr_measures):
                    worksheet.write(y,x+i, '', non_bold_style)
                if cell['height'] > 1:
                    L.append({'x': x, 'height':cell['height'] - 1})
                x = x + nbr_measures
            x, y = 1, y + 1

        # Step 2: measure row
        if nbr_measures > 1:
            worksheet.write(y,0, '', non_bold_style)
            for measure in jdata['measure_row']:
                style = bold_style if measure['is_bold'] else non_bold_style
                worksheet.write(y,x, measure['text'], style);
                x = x + 1
            y = y + 1

        # Step 3: writing data
        x = 0
        for row in jdata['rows']:
            worksheet.write(y, x, row['indent'] * '     ' + row['title'], non_bold_style)
            for cell in row['cells']:
                x = x + 1
                if cell.get('is_bold', False):
                    worksheet.write(y,x, cell['value'], bold)
                else:
                    worksheet.write(y,x, cell['value'])
            x, y = 0, y + 1

        fp = StringIO()
        workbook.save(fp)
        fp.seek(0)
        filecontent = fp.read()
        fp.close()

        return request.make_response(filecontent,
            headers=[('Content-Type', 'application/vnd.ms-excel'),
                    ('Content-Disposition', 'attachment; filename=table.xls;')],
            cookies={'fileToken': token})

