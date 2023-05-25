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
    send_by_post_warning_message = fields.Text(compute='_compute_send_by_post_warning_message')

    @api.depends('mode')
    def _compute_enable_send_by_post(self):
        for wizard in self:
            wizard.enable_send_by_post = wizard.mode in ('invoice_single', 'invoice_multi') \
                and all(x.state == 'posted' for x in wizard.move_ids)

    @api.depends('send_by_post_warning_message')
    def _compute_checkbox_send_by_post(self):
        for wizard in self:
            wizard.checkbox_send_by_post = not wizard.send_by_post_warning_message \
                and wizard.company_id.invoice_is_snailmail

    @api.depends('mode', 'checkbox_send_mail')
    def _compute_send_by_post_warning_message(self):
        for wizard in self:
            display_messages = []
            if wizard.enable_send_by_post and wizard.checkbox_send_mail:
                wrong_address_partners = wizard.move_ids.partner_id\
                    .filtered(lambda x: not self.env['snailmail.letter']._is_valid_address(x))
                if wrong_address_partners:
                    display_messages.append(_("The following customers don't have a valid address: "))
                    display_messages.append(", ".join(wrong_address_partners.mapped('name')))
            wizard.send_by_post_warning_message = "".join(display_messages) if display_messages else None

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

    def _generate_documents_success_hook(self, moves, from_cron):
        # EXTENDS 'account'
        moves = super()._generate_documents_success_hook(moves, from_cron)

        send_by_post = self.enable_send_by_post and self.checkbox_send_by_post

        if send_by_post:
            self.env['snailmail.letter']\
                .create([
                    self._prepare_snailmail_letter_values(move)
                    for move in moves
                ])\
                ._snailmail_print(immediate=False)

        return moves
