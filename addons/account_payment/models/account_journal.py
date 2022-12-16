# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, Command, models
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.constrains('inbound_payment_method_line_ids')
    def _check_inbound_payment_method_line_ids(self):
        """
        Check and ensure that the user do not remove a apml that is linked to a provider in the test or enabled state.
        """
        if not self.company_id:
            return

        self.env['account.payment.method'].flush_model(['code', 'payment_type'])
        self.env['account.payment.method.line'].flush_model(['payment_method_id'])
        self.env['payment.provider'].flush_model(['code', 'state'])

        self._cr.execute('''
            SELECT provider.id
              FROM payment_provider provider
              JOIN account_payment_method apm
                ON apm.code = provider.code
         LEFT JOIN account_payment_method_line apml
                ON apm.id = apml.payment_method_id AND apml.journal_id IS NOT NULL
             WHERE provider.state IN ('enabled', 'test')
               AND provider.code != 'custom'
               AND apm.payment_type = 'inbound'
               AND apml.id IS NULL
               AND provider.company_id IN %(company_ids)s
        ''', {'company_ids': tuple(self.company_id.ids)})
        ids = [r[0] for r in self._cr.fetchall()]
        if ids:
            providers = self.env['payment.provider'].sudo().browse(ids)
            raise UserError(
                _("You can't delete a payment method that is linked to a provider in the enabled or test state.\n"
                  "Linked provider(s): %s", ', '.join(p.display_name for p in providers))
            )

    def _get_available_payment_method_lines(self, payment_type):
        lines = super()._get_available_payment_method_lines(payment_type)

        return lines.filtered(lambda l: l.payment_provider_state != 'disabled')

    @api.depends('outbound_payment_method_line_ids', 'inbound_payment_method_line_ids')
    def _compute_available_payment_method_ids(self):
        super()._compute_available_payment_method_ids()

        installed_providers = self.env['payment.provider'].sudo().search([])
        method_information = self.env['account.payment.method']._get_payment_method_information()
        pay_methods = self.env['account.payment.method'].search([('code', 'in', list(method_information.keys()))])
        pay_method_by_code = {x.code + x.payment_type: x for x in pay_methods}

        # On top of the basic filtering, filter to hide unavailable providers.
        # This avoid allowing payment method lines linked to a provider that has no record.
        for code, vals in method_information.items():
            payment_method = pay_method_by_code.get(code + 'inbound')

            if not payment_method:
                continue

            for journal in self:
                to_remove = []

                available_providers = installed_providers.filtered(
                    lambda p: p.company_id == journal.company_id
                ).mapped('code')
                available = payment_method.code in available_providers

                if vals['mode'] == 'unique' and not available:
                    to_remove.append(payment_method.id)

                journal.available_payment_method_ids = [Command.unlink(payment_method) for payment_method in to_remove]
