from openerp import http
import simplejson
from openerp.tools import ustr
from openerp.http import request, serialize_exception as _serialize_exception
from cStringIO import StringIO
from collections import deque

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
        worksheet = workbook.add_sheet(jdata['title'][:30])
        header_bold = xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour gray25;")
        header_plain = xlwt.easyxf("pattern: pattern solid, fore_colour gray25;")
        bold = xlwt.easyxf("font: bold on;")

        # Step 1: writing headers
        headers = jdata['headers']

        # x,y: current coordinates 
        # carry: queue containing cell information when a cell has a >= 2 height
        #      and the drawing code needs to add empty cells below
        x, y, carry = 1, 0, deque()  
        for i, header_row in enumerate(headers):
            worksheet.write(i,0, '', header_plain)
            for header in header_row:
                while (carry and carry[0]['x'] == x):
                    cell = carry.popleft()
                    for i in range(nbr_measures):
                        worksheet.write(y, x+i, '', header_plain)
                    if cell['height'] > 1:
                        carry.append({'x': x, 'height':cell['height'] - 1})
                    x = x + nbr_measures
                style = header_plain if 'expanded' in header else header_bold
                for i in range(header['width']):
                    worksheet.write(y, x + i, header['title'] if i == 0 else '', style)
                if header['height'] > 1:
                    carry.append({'x': x, 'height':header['height'] - 1})
                x = x + header['width'];
            while (carry and carry[0]['x'] == x):
                cell = carry.popleft()
                for i in range(nbr_measures):
                    worksheet.write(y, x+i, '', header_plain)
                if cell['height'] > 1:
                    carry.append({'x': x, 'height':cell['height'] - 1})
                x = x + nbr_measures
            x, y = 1, y + 1

        # Step 2: measure row
        if nbr_measures > 1:
            worksheet.write(y,0, '', header_plain)
            for measure in jdata['measure_row']:
                style = header_bold if measure['is_bold'] else header_plain
                worksheet.write(y, x, measure['text'], style);
                x = x + 1
            y = y + 1

        # Step 3: writing data
        x = 0
        for row in jdata['rows']:
            worksheet.write(y, x, row['indent'] * '     ' + ustr(row['title']), header_plain)
            for cell in row['cells']:
                x = x + 1
                if cell.get('is_bold', False):
                    worksheet.write(y, x, cell['value'], bold)
                else:
                    worksheet.write(y, x, cell['value'])
            x, y = 0, y + 1

        response = request.make_response(None,
            headers=[('Content-Type', 'application/vnd.ms-excel'),
                    ('Content-Disposition', 'attachment; filename=table.xls;')],
            cookies={'fileToken': token})
        workbook.save(response.stream)

        return response
