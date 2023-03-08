# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models


_logger = logging.getLogger(__name__)

DEFAULT_FACTUR_ITALIAN_DATE_FORMAT = '%Y-%m-%d'


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_it_edi_transaction = fields.Char(copy=False, string="FatturaPA Transaction")
    l10n_it_edi_attachment_id = fields.Many2one('ir.attachment', copy=False, string="FatturaPA Attachment", ondelete="restrict")

    def send_pec_mail(self):
        self.ensure_one()
        # OVERRIDE
        # With SdiCoop web-service, no need to send PEC mail.
        # Set the state to 'other' because the invoice should not be managed par l10n_it_edi.
        self.l10n_it_send_state = 'other'

    @api.depends('l10n_it_edi_transaction')
    def _compute_show_reset_to_draft_button(self):
        super(AccountMove, self)._compute_show_reset_to_draft_button()
        for move in self.filtered(lambda m: m.l10n_it_edi_transaction):
            move.show_reset_to_draft_button = False
