from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_sending_method = fields.Selection(
        selection_add=[('snailmail', 'by Post')],
    )
