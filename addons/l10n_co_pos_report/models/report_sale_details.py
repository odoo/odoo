# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.osv.expression import AND


class PosOrder(models.AbstractModel):
    _name = 'report.l10n_co_pos_report.report_saledetails'
    _inherit = 'report.point_of_sale.report_saledetails'
    _description = 'Point of Sale Details'

    @api.model
    def prepare_sale_details(self, domain, date_start, date_stop, config_ids, session_ids, include_products):
        result = super(PosOrder, self).prepare_sale_details(domain, date_start, date_stop, config_ids, session_ids, include_products)
        result['include_products'] = include_products
        orders = self.env['pos.order'].search(domain)
        if len(config_ids) == 1:
            result.update({
                'pos_config': orders.mapped('config_id'),
                'config_name': orders.mapped('config_id').name,
                'include_products': include_products,
                'first_ref': orders and orders[-1].name,
                'last_ref': orders and orders[0].name,
                'total_payment_count': sum(payment.get('count') for payment in result.get('payments')),
            })
        return result
