# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, Command, models
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_available_payment_method_lines(self, payment_type):
        lines = super()._get_available_payment_method_lines(payment_type)

        return lines.filtered(lambda l: l.payment_acquirer_state != 'disabled')

    @api.depends('outbound_payment_method_line_ids', 'inbound_payment_method_line_ids')
    def _compute_available_payment_method_ids(self):
        super()._compute_available_payment_method_ids()

        installed_acquirers = self.env['payment.acquirer'].sudo().search([])
        method_information = self.env['account.payment.method']._get_payment_method_information()
        pay_methods = self.env['account.payment.method'].search([('code', 'in', list(method_information.keys()))])
        pay_method_by_code = {x.code + x.payment_type: x for x in pay_methods}

        # On top of the basic filtering, filter to hide unavailable acquirers.
        # This avoid allowing payment method lines linked to an acquirer that has no record.
        for code, vals in method_information.items():
            payment_method = pay_method_by_code.get(code + 'inbound')

            if not payment_method:
                continue

            for journal in self:
                to_remove = []

                available_providers = installed_acquirers.filtered(
                    lambda a: a.company_id == journal.company_id
                ).mapped('provider')
                available = payment_method.code in available_providers

                if vals['mode'] == 'unique' and not available:
                    to_remove.append(payment_method.id)

                journal.available_payment_method_ids = [Command.unlink(payment_method) for payment_method in to_remove]

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
