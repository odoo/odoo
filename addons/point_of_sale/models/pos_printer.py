# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

class PosPrinter(models.Model):

    _name = 'pos.printer'
    _description = 'Point of Sale Printer'
    _inherit = ['pos.load.mixin']

    name = fields.Char('Printer Name', required=True, default='Printer', help='An internal identification of the printer')
    printer_type = fields.Selection(string='Printer Type', default='iot',
        selection=[('iot', ' Use a printer connected to the IoT Box')])
    proxy_ip = fields.Char('Proxy IP Address', help="The IP Address or hostname of the Printer's hardware proxy")
    product_categories_ids = fields.Many2many('pos.category', 'printer_category_rel', 'printer_id', 'category_id', string='Printed Product Categories')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.model
    def _load_pos_data_domain(self, data):
        return [('id', 'in', data['pos.config']['data'][0]['printer_ids'])]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'proxy_ip', 'product_categories_ids', 'printer_type']
