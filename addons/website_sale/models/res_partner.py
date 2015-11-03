# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import openerp


class res_partner(openerp.models.Model):
    _inherit = 'res.partner'

    last_website_so_id = openerp.fields.Many2one('sale.order', 'Last Online Sale Order')
