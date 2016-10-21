# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleConfigSettings(models.TransientModel):
    _name = 'sale.config.settings'
    _inherit = 'res.config.settings'

    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.user.company_id)
    module_crm = fields.Boolean("CRM")
    module_sale = fields.Boolean("Sales")
    module_website_sign = fields.Boolean("eSign")
    module_helpdesk = fields.Boolean("Helpdesk")
    module_sale_contract = fields.Boolean("Subscriptions")
    module_account_accountant = fields.Boolean("Accounting")
