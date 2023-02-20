# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.http import request
from werkzeug.urls import url_quote

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    # FIXME: the select box has three optios: null; table; kiosk 
    # --> make it so that it only has two options: table; kiosk
    pos_self_order_location = fields.Selection([
        ('table', 'Table'),
        ('kiosk', 'Kiosk')],
        compute='_compute_pos_module_pos_self_order', store=True, readonly=False)
    pos_self_order_allow_open_tabs = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')],
        compute='_compute_pos_module_pos_self_order', store=True, readonly=False)

    @api.depends('pos_module_pos_self_order', 'pos_config_id')
    def _compute_pos_module_pos_self_order(self):
        for res_config in self:
            if not res_config.pos_module_pos_self_order:
                res_config.update({
                    'pos_self_order_location': False,
                    'pos_self_order_allow_open_tabs': False,
                })
            else:
                res_config.update({
                    'pos_self_order_location': res_config.pos_config_id.self_order_location,
                    'pos_self_order_allow_open_tabs': res_config.pos_config_id.self_order_allow_open_tabs,
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