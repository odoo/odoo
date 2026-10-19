from odoo import fields, models


class L10nSaEdiTransactionType(models.Model):
    _name = 'l10n_sa_edi.transaction.type'
    _description = 'ZATCA Transaction Type'

    name = fields.Char(string="Name", translate=True, required=True)
    code = fields.Selection(
        selection=[
            ('export', 'Export'),
            ('summary', 'Summary'),
            ('nominal', 'Nominal'),
        ],
        string="Code",
        required=True,
    )
