# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import models, fields
from odoo.exceptions import UserError
from odoo.addons.l10n_hu_edi.models.l10n_hu_edi_connection import L10nHuEdiConnection


class L10n_Hu_EdiCancellation(models.TransientModel):
    _name = 'l10n_hu_edi.cancellation'
    _description = 'Technical Annulment Wizard'

    invoice_id = fields.Many2one(
        comodel_name='account.move',
        string='Invoice to cancel',
    )
    code = fields.Selection(
        selection=[
            ('ERRATIC_DATA', 'ERRATIC_DATA - Erroneous data'),
            ('ERRATIC_INVOICE_NUMBER', 'ERRATIC_INVOICE_NUMBER - Erroneous invoice number'),
            ('ERRATIC_INVOICE_ISSUE_DATE', 'ERRATIC_INVOICE_ISSUE_DATE - Erroneous issue date'),
        ],
        string='Annulment Code',
        required=True,
    )
    reason = fields.Char(
        string='Annulment Reason',
        required=True,
    )

    def button_request_cancel(self):
        with L10nHuEdiConnection(self.env) as connection:
            self.invoice_id._l10n_hu_edi_acquire_lock()
            self.invoice_id._l10n_hu_edi_request_cancel(connection, self.code, self.reason)

            if 'query_status' in self.invoice_id._l10n_hu_edi_get_valid_actions():
                time.sleep(2)
                self.invoice_id._l10n_hu_edi_query_status(connection)

        formatted_message = self.env['account.move.send']._format_error_html(self.invoice_id.l10n_hu_edi_messages)
        self.invoice_id.message_post(body=formatted_message)

        if self.env['account.move.send']._can_commit():
            self.env.cr.commit()

        if self.invoice_id.l10n_hu_edi_messages.get('blocking_level') == 'error':
            raise UserError(self.env['account.move.send']._format_error_text(self.invoice_id.l10n_hu_edi_messages))
