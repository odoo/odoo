# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMoveReversal(models.TransientModel):

    _inherit = "account.move.reversal"

    l10n_latam_use_documents = fields.Boolean(
        related='move_id.journal_id.l10n_latam_use_documents', readonly=True)
    l10n_latam_document_type_id = fields.Many2one('l10n_latam.document.type', 'Document Type', ondelete='cascade')
    l10n_latam_sequence_id = fields.Many2one('ir.sequence', compute='_compute_l10n_latam_sequence')
    l10n_latam_document_number = fields.Char(string='Document Number')

    @api.model
    def default_get(self, fields):
        res = super(AccountMoveReversal, self).default_get(fields)
        move_ids = self.env['account.move'].browse(self.env.context['active_ids']) if self.env.context.get('active_model') == 'account.move' else self.env['account.move']
        if len(move_ids) > 1:
            move_ids_use_document = move_ids.filtered(lambda move: move.l10n_latam_use_documents)
            if move_ids_use_document:
                raise UserError(_('You can only reverse documents with legal invoicing documents from Latin America one at a time.\nProblematic documents: %s') % ", ".join(move_ids_use_document.mapped('name')))

        return res

    @api.model
    def _reverse_type_map(self, move_type):
        match = {
            'entry': 'entry',
            'out_invoice': 'out_refund',
            'in_invoice': 'in_refund',
            'in_refund': 'in_invoice',
            'out_receipt': 'in_receipt',
            'in_receipt': 'out_receipt'}
        return match.get(move_type)

    @api.onchange('move_id')
    def _onchange_move_id(self):
        if self.move_id.l10n_latam_use_documents:
            refund = self.move_id.new({
                'type': self._reverse_type_map(self.move_id.type),
                'journal_id': self.move_id.journal_id.id,
                'partner_id': self.move_id.partner_id.id,
                'company_id': self.move_id.company_id.id,
            })
            self.l10n_latam_document_type_id = refund.l10n_latam_document_type_id
            return {'domain': {
                'l10n_latam_document_type_id': [('id', 'in', refund.l10n_latam_available_document_type_ids.ids)]}}

    def reverse_moves(self):
        return super(AccountMoveReversal, self.with_context(
            default_l10n_latam_document_type_id=self.l10n_latam_document_type_id.id,
            default_l10n_latam_document_number=self.l10n_latam_document_number)).reverse_moves()

    @api.depends('l10n_latam_document_type_id')
    def _compute_l10n_latam_sequence(self):
        for rec in self:
            refund = rec.move_id.new({
                'type': self._reverse_type_map(rec.move_id.type),
                'journal_id': rec.move_id.journal_id.id,
                'partner_id': rec.move_id.partner_id.id,
                'company_id': rec.move_id.company_id.id,
                'l10n_latam_document_type_id': rec.l10n_latam_document_type_id.id,
            })
            rec.l10n_latam_sequence_id = refund._get_document_type_sequence()

    @api.onchange('l10n_latam_document_number', 'l10n_latam_document_type_id')
    def _onchange_l10n_latam_document_number(self):
        if self.l10n_latam_document_type_id:
            l10n_latam_document_number = self.l10n_latam_document_type_id._format_document_number(
                self.l10n_latam_document_number)
            if self.l10n_latam_document_number != l10n_latam_document_number:
                self.l10n_latam_document_number = l10n_latam_document_number
