# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ReportPoint_Of_SaleReport_Saledetails(models.AbstractModel):
    _inherit = 'report.point_of_sale.report_saledetails'

    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False, **kwargs):
        data = super().get_sale_details(date_start, date_stop, config_ids, session_ids, **kwargs)
        orders = self.env['pos.order'].search(self._get_domain(date_start, date_stop, config_ids, session_ids, **kwargs))
        global_discount_lines = orders.lines.filtered(lambda l: l.product_id.id == l.order_id.config_id.discount_product_id.id)
        data['global_discount_number'] = len(global_discount_lines.order_id)
        data['global_discount_amount'] = sum(global_discount_lines.mapped('price_subtotal_incl')) * -1
        return data
