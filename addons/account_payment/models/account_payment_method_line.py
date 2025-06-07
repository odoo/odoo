# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression


class AccountPaymentMethodLine(models.Model):
    _inherit = "account.payment.method.line"

    payment_provider_id = fields.Many2one(
        comodel_name='payment.provider',
        compute='_compute_payment_provider_id',
        store=True,
        readonly=False,
        domain="[('code', '=', code)]",
    )
    payment_provider_state = fields.Selection(
        related='payment_provider_id.state'
    )

    @api.depends('payment_provider_id.name')
    def _compute_name(self):
        super()._compute_name()
        for line in self:
            if line.payment_provider_id and not line.name:
                line.name = line.payment_provider_id.name

    @api.depends('payment_method_id')
    def _compute_payment_provider_id(self):
        results = self.journal_id._get_journals_payment_method_information()
        manage_providers = results['manage_providers']
        method_information_mapping = results['method_information_mapping']
        providers_per_code = results['providers_per_code']

        for line in self:
            journal = line.journal_id
            company = journal.company_id
            if (
                company
                and line.payment_method_id
                and not line.payment_provider_id
                and manage_providers
                and method_information_mapping.get(line.payment_method_id.id, {}).get('mode') == 'electronic'
            ):
                provider_ids = providers_per_code.get(company.id, {}).get(line.code, set())

                # Exclude the 'unique' / 'electronic' values that are already set on the journal.
                protected_provider_ids = set()
                for payment_type in ('inbound', 'outbound'):
                    lines = journal[f'{payment_type}_payment_method_line_ids']
                    for journal_line in lines:
                        if journal_line.payment_method_id:
                            if (
                                manage_providers
                                and method_information_mapping.get(journal_line.payment_method_id.id, {}).get('mode') == 'electronic'
                            ):
                                protected_provider_ids.add(journal_line.payment_provider_id.id)

                candidates_provider_ids = provider_ids - protected_provider_ids
                if candidates_provider_ids:
                    line.payment_provider_id = next(iter(candidates_provider_ids))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_active_provider(self):
        """ Ensure we don't remove an account.payment.method.line that is linked to a provider
        in the test or enabled state.
        """
        active_provider = self.payment_provider_id.filtered(lambda provider: provider.state in ['enabled', 'test'])
        if active_provider:
            raise UserError(_(
                "You can't delete a payment method that is linked to a provider in the enabled "
                "or test state.\n""Linked providers(s): %s",
                ', '.join(a.display_name for a in active_provider),
            ))

    def action_open_provider_form(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Provider'),
            'view_mode': 'form',
            'res_model': 'payment.provider',
            'target': 'current',
            'res_id': self.payment_provider_id.id
        }
