# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountMoveSend(models.Model):
    _inherit = 'account.move.send'

    enable_send_by_post = fields.Boolean(compute='_compute_enable_send_by_post')
    send_by_post = fields.Boolean(
        string="By Post",
        compute='_compute_send_by_post',
        store=True,
        readonly=False,
    )
    send_by_post_warning_message = fields.Text(compute='_compute_send_by_post_warning_message')

    @api.depends('enable_send_by_post', 'send_by_post')
    def _compute_button_name(self):
        super()._compute_button_name()
        for wizard in self:
            if not wizard.button_name and wizard.enable_send_by_post and wizard.send_by_post:
                wizard.button_name = _("Send")

    @api.depends('mode')
    def _compute_enable_send_by_post(self):
        for wizard in self:
            wizard.enable_send_by_post = wizard.mode in ('invoice_single', 'invoice_multi') \
                                         and all(x.state == 'posted' for x in wizard.move_ids)

    @api.depends('send_by_post_warning_message')
    def _compute_send_by_post(self):
        for wizard in self:
            wizard.send_by_post = not wizard.send_by_post_warning_message \
                                  and wizard.company_id.invoice_is_snailmail

    @api.depends('mode')
    def _compute_send_by_post_warning_message(self):
        for wizard in self:
            display_messages = []
            if wizard.enable_send_by_post:
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
            'attachment_id': move.pdf_report_id.id,
        }

    def action_send_and_print(self, from_cron=False):
        # EXTENDS 'account'
        results = super().action_send_and_print(from_cron=from_cron)

        send_by_post = self.enable_send_by_post and self.send_by_post

        if send_by_post:
            if self.mode == 'invoice_single':
                self.env['snailmail.letter']\
                    .create(self._prepare_snailmail_letter_values(self.move_ids))\
                    ._snailmail_print(immediate=False)
            elif from_cron and self.mode == 'invoice_multi':
                self.env['snailmail.letter']\
                    .create([
                        self._prepare_snailmail_letter_values(move)
                        for move in self.move_ids
                    ])\
                    ._snailmail_print(immediate=False)

        return results
