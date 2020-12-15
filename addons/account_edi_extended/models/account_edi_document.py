# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, _
import logging

_logger = logging.getLogger(__name__)
DEFAULT_BLOCKING_LEVEL = 'warning'  # Keep previous behavior. TODO : when account_edi_extended is merged with account_edi, should be 'error' (document will not be processed again until forced retry or reset to draft)


class AccountEdiDocument(models.Model):
    _inherit = 'account.edi.document'

    blocking_level = fields.Selection(selection=[('info', 'Info'), ('warning', 'Warning'), ('error', 'Error')],
                                     help="Blocks the document current operation depending on the error severity :\n"
                                          "  * Info: the document is not blocked and everything is working as it should.\n"
                                          "  * Warning : there is an error that doesn't prevent the current Electronic Invoicing operation to succeed.\n"
                                          "  * Error : there is an error that blocks the current Electronic Invoicing operation.")

    def _check_move_configuration(self):
        # OVERRIDE
        for document in self:
            errors = document.edi_format_id._check_move_configuration(document.move_id)
            if errors:
                # Errors are just informative at this point, _process_job will still be called on these documents
                document.error = self.env['account.edi.format']._format_error_message(_('Invalid configuration:'), errors)
                document.blocking_level = 'info'
