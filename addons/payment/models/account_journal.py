# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, Command, models
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_available_payment_method_lines(self, payment_type):
        lines = super()._get_available_payment_method_lines(payment_type)

        return lines.filtered(lambda l: l.payment_acquirer_state != 'disabled')

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_to_payment_acquirer(self):
        linked_acquirers = self.env['payment.acquirer'].sudo().search([]).filtered(
            lambda acq: acq.journal_id.id in self.ids and acq.state != 'disabled'
        )
        if linked_acquirers:
            raise UserError(_(
                "You must first deactivate a payment acquirer before deleting its journal.\n"
                "Linked acquirer(s): %s", ', '.join(acq.display_name for acq in linked_acquirers)
            ))
