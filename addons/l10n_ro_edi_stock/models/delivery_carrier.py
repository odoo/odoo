from odoo import fields, models


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    l10n_ro_edi_stock_partner_id = fields.Many2one(comodel_name='res.partner', string="Partner")
