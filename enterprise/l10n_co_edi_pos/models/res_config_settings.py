from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = ['res.config.settings']

    pos_l10n_co_edi_pos_serial_number = fields.Char(related='pos_config_id.l10n_co_edi_pos_serial_number', readonly=False)
    pos_l10n_co_edi_credit_note_journal_id = fields.Many2one(
        comodel_name='account.journal',
        related='pos_config_id.l10n_co_edi_credit_note_journal_id',
        readonly=False,
    )
    pos_l10n_co_edi_final_consumer_invoices_journal_id = fields.Many2one(
        comodel_name='account.journal',
        related='pos_config_id.l10n_co_edi_final_consumer_invoices_journal_id',
        readonly=False,
    )
