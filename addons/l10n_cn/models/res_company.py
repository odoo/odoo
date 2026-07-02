from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_cn_output_vat_offset_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Output VAT Offset Account",
    )
    l10n_cn_output_vat_offset_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Output VAT Offset Journal",
    )
