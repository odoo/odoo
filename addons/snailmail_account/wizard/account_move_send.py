# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountMoveSend(models.Model):
    _inherit = 'account.move.send'

    enable_send_by_post = fields.Boolean(compute='_compute_enable_send_by_post')
    checkbox_send_by_post = fields.Boolean(
        string="By Post",
        compute='_compute_checkbox_send_by_post',
        store=True,
        readonly=False,
    )
    send_by_post_cost = fields.Integer(string='Stamps', compute='_compute_send_by_post_extra_fields')
    send_by_post_warning_message = fields.Text(compute='_compute_send_by_post_extra_fields')
    send_by_post_readonly = fields.Boolean(compute='_compute_send_by_post_extra_fields')

    def _get_available_field_values_in_multi(self, move):
        # EXTENDS 'account'
        values = super()._get_available_field_values_in_multi(move)
        values['checkbox_send_by_post'] = self.checkbox_send_by_post
        return values

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('mode')
    def _compute_enable_send_by_post(self):
        for wizard in self:
            wizard.enable_send_by_post = wizard.mode in ('invoice_single', 'invoice_multi') \
                and all(x.state == 'posted' for x in wizard.move_ids)

    @api.depends('company_id')
    def _compute_checkbox_send_by_post(self):
        for wizard in self:
            wizard.checkbox_send_by_post = wizard.company_id.invoice_is_snailmail

    @api.depends('mode', 'checkbox_send_by_post')
    def _compute_send_by_post_extra_fields(self):
        for wizard in self:
            partner_with_valid_address = wizard.move_ids.partner_id \
                .filtered(self.env['snailmail.letter']._is_valid_address)
            wizard.send_by_post_cost = len(partner_with_valid_address)
            wizard.send_by_post_readonly = not partner_with_valid_address
            wizard.send_by_post_warning_message = False

            if wizard.enable_send_by_post and wizard.checkbox_send_by_post:
                invoice_without_valid_address = wizard.move_ids.filtered(
                    lambda move: not self.env['snailmail.letter']._is_valid_address(move.partner_id))
                if invoice_without_valid_address:
                    wizard.send_by_post_warning_message = _(
                        "The partners on the following invoices have no valid address, "
                        "so those invoices will not be sent: %s"
                    ) % ", ".join(invoice_without_valid_address.mapped('name'))

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    @api.model
    def _prepare_snailmail_letter_values(self, move):
        return {
            'partner_id': move.partner_id.id,
            'model': 'account.move',
            'res_id': move.id,
            'user_id': self.env.user.id,
            'company_id': move.company_id.id,
            'attachment_id': move.invoice_pdf_report_id.id,
        }

    def _hook_if_success(self, moves_data, from_cron=False, allow_fallback_pdf=False):
        # EXTENDS 'account'
        super()._hook_if_success(moves_data, from_cron=from_cron, allow_fallback_pdf=allow_fallback_pdf)

        send_by_post = self.enable_send_by_post and self.checkbox_send_by_post
        if not send_by_post:
            return

        moves = self.env['account.move']
        for move in moves_data:
            moves |= move
        moves = moves.filtered('invoice_pdf_report_id')
        if not moves:
            return

        self.env['snailmail.letter']\
            .create([
                self._prepare_snailmail_letter_values(move)
                for move in moves
            ])\
            ._snailmail_print(immediate=False)
