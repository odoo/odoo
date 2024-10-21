from odoo.addons.l10n_it_edi_ndd.models.account_payment_methode_line import L10N_IT_PAYMENT_METHOD_SELECTION
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_it_payment_method = fields.Selection(
        selection=L10N_IT_PAYMENT_METHOD_SELECTION,
        compute='_compute_l10n_it_payment_method',
        store=True,
        readonly=False,
    )

    l10n_it_document_type = fields.Many2one(
        comodel_name='l10n_it.document.type',
        compute='_compute_l10n_it_document_type',
        store=True,
        readonly=False,
    )

    @api.depends('line_ids.matching_number', 'payment_state', 'matched_payment_ids')
    def _compute_l10n_it_payment_method(self):
        if self.env.company.account_fiscal_country_id.code != 'IT':
            return

        move_lines_per_matching_number = self.env['account.move.line'].search([
            ('matching_number', 'in', self.line_ids.filtered('matching_number').mapped('matching_number')),
            ('company_id', '=', self.env.company.id),
        ]).grouped('matching_number')

        for move in self:
            matching_numbers = move.line_ids.filtered('matching_number').mapped('matching_number')
            if matching_numbers:
                # We use matching_numbers[0] directly, assuming there's a valid key in the dictionary.
                matching_lines = move_lines_per_matching_number.get(matching_numbers[0])
                if matching_lines and matching_lines.payment_id:
                    payment_method_line = matching_lines.payment_id.payment_method_line_id[0]
                    if payment_method_line:
                        move.l10n_it_payment_method = payment_method_line.l10n_it_payment_method
                        continue  # Skip to the next move
            if linked_payment := move.matched_payment_ids.filtered(lambda p: p.state != 'draft')[:1]:
                move.l10n_it_payment_method = linked_payment.payment_method_line_id.l10n_it_payment_method
                continue

            # Default handling if no valid matching lines found or if conditions don't match
            move.l10n_it_payment_method = move.origin_payment_id.payment_method_line_id.l10n_it_payment_method or move.l10n_it_payment_method or 'MP05'

    @api.depends('state')
    def _compute_l10n_it_document_type(self):
        document_type = self.env['l10n_it.document.type'].search([]).grouped('code')
        for move in self:
            if move.country_code != 'IT' or move.l10n_it_document_type or move.state != 'posted':
                continue

            move.l10n_it_document_type = document_type.get(move._l10n_it_edi_get_document_type())

    def _l10n_it_edi_get_values(self, pdf_values=None):
        # EXTENDS 'l10n_it_edi'
        res = super()._l10n_it_edi_get_values(pdf_values)
        res['document_type'] = self.l10n_it_document_type.code
        res['payment_method'] = self.l10n_it_payment_method

        return res

    def _reverse_moves(self, default_values_list=None, cancel=False):
        """
            This function is needed because the l10n_it_document_type is set only if no value are set when posting it
            But when reversing the move, the document type of the original move is copied and so it isn't recomputed.
        """
        # EXTENDS account
        reverse_moves = super()._reverse_moves(default_values_list, cancel)
        for move in reverse_moves:
            move.l10n_it_document_type = False
        return reverse_moves
