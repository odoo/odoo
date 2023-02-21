# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.http import request
from werkzeug.urls import url_quote

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    # FIXME: the select box has three optios: null; table; kiosk 
    self_order_pay_after = fields.Selection([
        ('each', 'Each Order'),
        ('meal', 'Meal')
        ],
        compute='_compute_pos_module_pos_self_order', store=True, readonly=False)

    @api.depends('pos_module_pos_self_order', 'pos_config_id')
    def _compute_pos_module_pos_self_order(self):
        for res_config in self:
            if not res_config.pos_module_pos_self_order:
                res_config.update({
                    'self_order_pay_after': False,
                })
            else:
                res_config.update({
                    'self_order_pay_after': res_config.pos_config_id.self_order_pay_after,
                })
    def generate_qr_codes_page(self):
        business_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        no_of_qr_codes_per_page = 9
        generic_qr_list = [{
                'id': 0,
                'url': url_quote(f"{business_url}/pos-self-order?pos_id={self.pos_config_id.id}"),
            } for i in range(0, no_of_qr_codes_per_page)]
        tables = list(map(lambda table: 
            {
                'url': url_quote(f"{business_url}/pos-self-order?pos_id={self.pos_config_id.id}&table_id={table['id']}"), 
                **table
            },self.pos_config_id.get_tables_order_count()))
        qr_codes_to_print = generic_qr_list + tables
        data = {
            'pos_name': self.pos_config_id.name,
            'groups_of_tables': splitListIntoNLists(qr_codes_to_print, no_of_qr_codes_per_page),
            }
        return self.env.ref('pos_self_order.report_self_order_qr_codes_page').report_action([], data=data)

def splitListIntoNLists(l, n):
    return [l[i:i + n] for i in range(0, len(l), n)]