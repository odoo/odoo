from odoo import fields, models


class L10nEsEdiVerifactuDocument(models.Model):
    _inherit = 'l10n_es_edi_verifactu.document'

    pos_order_id = fields.Many2one(
        string="PoS Order",
        comodel_name='pos.order',
        readonly=True,
    )
