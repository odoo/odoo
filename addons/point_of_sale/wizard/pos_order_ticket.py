# -*- coding: utf-8 -*-
import ast

from odoo import api, fields, models


class PosOrderTicket(models.TransientModel):
    _name = 'pos.order.ticket'
    _description = 'Pos Order Ticket Reprint'

    pos_config_id = fields.Many2one('pos.config', string="POS Name", required=True)
    ip_url = fields.Char(compute="_compute_ip_url")

    @api.depends('pos_config_id')
    def _compute_ip_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for wiz in self:
            pos_config = wiz.pos_config_id
            if not pos_config.proxy_ip.startswith('http') :
                if base_url.startswith("https"):
                    wiz.ip_url = "https://" + pos_config.proxy_ip
                else:
                    wiz.ip_url = "http://" + pos_config.proxy_ip + ":8069"

    def print_ticket(self):
        self.ensure_one()
        order_id = self.env.context.get('active_id')
        if not order_id:
            return
        order = self.env['pos.order'].browse(order_id)
        ticket_data = ast.literal_eval(order.pos_ticket_data)
        return {
            'type': 'ir.actions.client',
            'tag': 'print_ticket_action',
            'params': {'receipt_data': ticket_data, 'iot_box_url': self.ip_url},
        }
