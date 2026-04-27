from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_co_edi_pos_sequence_id = fields.Many2one(
        comodel_name='ir.sequence',
        copy=False,
        string='POS order name sequence',
        compute='_compute_l10n_co_edi_pos_sequence_id',
        store=True,
        readonly=False,
    )
    l10n_co_edi_pos_is_final_consumer = fields.Boolean(string="Journal for Final Consumer POS")

    @api.depends('l10n_co_edi_pos_is_final_consumer', 'company_id.l10n_co_edi_pos_dian_enabled')
    def _compute_l10n_co_edi_pos_sequence_id(self):
        for journal in self:
            if journal.company_id.l10n_co_edi_pos_dian_enabled:
                sequence = journal.l10n_co_edi_pos_sequence_id
                if not sequence and journal.l10n_co_edi_pos_is_final_consumer:
                    code = f'l10n_co_edi_pos.account.journal.{journal.id}'
                    sequence = self.env['ir.sequence'].search([('code', '=', code), ('company_id', '=', journal.company_id.id)], limit=1)
                    if not sequence:
                        sequence = self.env['ir.sequence'].create([{
                            'name': journal.name,
                            'code': code,
                            'company_id': journal.company_id.id,
                            'prefix': journal.code,
                            'number_next': journal.l10n_co_edi_min_range_number or 0,
                        }])
                journal.l10n_co_edi_pos_sequence_id = sequence
            else:
                journal.l10n_co_edi_pos_sequence_id = False

    @api.ondelete(at_uninstall=False)
    def _unlink_l10n_co_edi_pos_sequence(self):
        if self.l10n_co_edi_pos_sequence_id:
            self.l10n_co_edi_pos_sequence_id.unlink()

    @api.onchange('code')
    def _l10n_co_edi_pos_onchange_code(self):
        if self.code and self.l10n_co_edi_pos_sequence_id:
            self.l10n_co_edi_pos_sequence_id.prefix = self.code
