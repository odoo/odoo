# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models

class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    group_analytic_account_for_sales = fields.Boolean(
        'Analytic accounting for sales',
        implied_group='sale.group_analytic_accounting',
        help="Allows you to specify an analytic account on sales orders.")
