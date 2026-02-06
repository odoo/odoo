from odoo import models, fields

class PosConfig(models.Model):
    _inherit = 'pos.config'

    accept_remote_orders = fields.Boolean(string='Accept Remote Orders', help="If checked, this POS tablet will listen for and print external orders (Uber/Web)")
