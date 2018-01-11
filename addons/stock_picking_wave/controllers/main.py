from openerp.addons.web import http
from openerp.addons.web.http import request


class picking_wave_report(http.Controller):
    @http.route('/report/stock_picking_wave.report_pickingwave/<ids>', type='http', auth='user', 
                website=True)
    def report_picking_wave(self, ids):
        self.cr, self.uid, self.pool = request.cr, request.uid, request.registry
        ids = [int(i) for i in ids.split(',')]
        picking_wave_obj = self.pool["stock.picking.wave"]
        wave = picking_wave_obj.browse(self.cr, self.uid, ids[0])
        docargs = {
            'docs': wave.picking_ids,
        }
        return request.registry['report'].render(self.cr, self.uid, [], 'stock.report_picking', docargs)
