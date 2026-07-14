from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_exp_date_on_invoice = fields.Boolean("Display Expiration Dates on Invoices",
        implied_group='sale_stock_product_expiry.group_exp_date_on_invoice')
