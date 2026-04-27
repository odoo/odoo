from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    intercompany_generate_sales_orders = fields.Boolean(related='company_id.intercompany_generate_sales_orders', readonly=False)
    intercompany_generate_purchase_orders = fields.Boolean(related='company_id.intercompany_generate_purchase_orders', readonly=False)
