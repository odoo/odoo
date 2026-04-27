from odoo import models, fields


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _default_l10n_co_edi_credit_note_journal(self):
        return self.env['account.journal'].search([
            *self.env['account.journal']._check_company_domain(self.env.company),
            ('type', '=', 'sale'),
        ], limit=1)

    def _default_l10n_co_edi_final_consumer_invoices_journal(self):
        return self.env['account.journal'].search([
            *self.env['account.journal']._check_company_domain(self.env.company),
            ('type', '=', 'sale'),
        ], limit=1)

    l10n_co_edi_pos_serial_number = fields.Char(string="POS Serial Number")
    l10n_co_edi_credit_note_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Credit Notes",
        check_company=True,
        domain=[('type', '=', 'sale')],
        default=_default_l10n_co_edi_credit_note_journal,
    )
    l10n_co_edi_final_consumer_invoices_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="Final Consumer Invoices",
        check_company=True,
        domain=[('type', '=', 'sale')],
        default=_default_l10n_co_edi_final_consumer_invoices_journal,
    )
