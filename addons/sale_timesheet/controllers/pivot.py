import json

from odoo import http, _
from odoo.http import request
from odoo.tools import float_round
from odoo.addons.web.controllers.pivot import TableExporter


class PivotExporter(TableExporter):

    @http.route('/web/pivot/export_xlsx', type='http', auth="user")
    def export_xlsx(self, data, **kw):
        jdata = self.convert_columns(data)
        return super().export_xlsx(json.dumps(jdata), **kw)

    def convert_columns(self, data):
        """
        Backend data are all in hours. Widget converts the uom (hours > day) only for the frontend pivot view
        The function is to handle it error-proof for downloading xlsx feature
        """

        dict_data = json.loads(data)
        indexes = []
        index = 0
        if dict_data['model'] == 'timesheets.analysis.report':

            hours_uom = request.env.ref('uom.product_uom_hour', raise_if_not_found=False)
            if not hours_uom:
                return dict_data

            for col in dict_data['measure_headers']:
                if _('Days Spent').lower() in col['title'].lower():
                    indexes.append(index)
                index += 1

            for index in indexes:
                for row in dict_data['rows']:
                    col = row['values'][index]
                    if col['value']:  # skip null
                        try:
                            col['value'] = str(float_round(float(col['value']) / hours_uom.factor, precision_digits=2, rounding_method='UP'))
                        except Exception:
                            continue
        return dict_data
