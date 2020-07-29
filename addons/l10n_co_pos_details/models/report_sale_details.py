# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class PosOrder(models.AbstractModel):
    _name = 'report.l10n_co_pos_details.report_saledetails'
    _inherit = 'report.point_of_sale.report_saledetails'
    _description = 'Point of Sale Details'

    @api.model
    def _prepare_sale_details(self, orders, domain, date_start, date_stop, config_ids, session_ids):
        result = super(PosOrder, self)._prepare_sale_details(orders, domain, date_start, date_stop, config_ids, session_ids)
        result.update({
            'pos_config': self.env['pos.config'].browse(config_ids),
            'first_ref': orders and orders[-1].name,
            'last_ref': orders and orders[0].name,
            'total_payment_count': sum(payment.get('count', 0.0) for payment in result.get('payments')),
        })
        return result

    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        configs = self.env['pos.config'].browse(data['config_ids'])
        sale_details = self.get_sale_details(data['date_start'], data['date_stop'], configs.ids)
        sale_details['include_products'] = data['include_products']
        data.update(sale_details)
        return data
