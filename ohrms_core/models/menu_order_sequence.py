from odoo import fields, models, api


class MenuOldSequenceNumber(models.Model):
    _inherit = 'ir.ui.menu'

    recent_menu_sequence = fields.Integer(default=None)
    order_changed = fields.Boolean(default=False)
