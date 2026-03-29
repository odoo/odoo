# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression


class AccountPaymentMethodLine(models.Model):
    _inherit = "account.payment.method.line"

    payment_acquirer_id = fields.Many2one(
        comodel_name='payment.acquirer',
        compute='_compute_payment_acquirer_id',
        store=True,
        readonly=False,
    )
    payment_acquirer_state = fields.Selection(
        related='payment_acquirer_id.state'
    )

    @api.depends('payment_method_id')
    def _compute_payment_acquirer_id(self):
        results = self.journal_id._get_journals_payment_method_information()
        manage_acquirers = results['manage_acquirers']
        method_information_mapping = results['method_information_mapping']
        acquirers_per_code = results['acquirers_per_code']

        for line in self:
            journal = line.journal_id
            company = journal.company_id
            if (
                company
                and line.payment_method_id
                and manage_acquirers
                and line.payment_method_id.id in method_information_mapping
                and method_information_mapping[line.payment_method_id.id]['mode'] == 'electronic'
            ):
                acquirer_ids = acquirers_per_code.get(company.id, {}).get(line.code, set())

                # Exclude the 'unique' / 'electronic' values that are already set on the journal.
                protected_acquirer_ids = set()
                for payment_type in ('inbound', 'outbound'):
                    lines = journal[f'{payment_type}_payment_method_line_ids']
                    for journal_line in lines:
                        if journal_line.payment_method_id and journal_line.payment_method_id.id in method_information_mapping:
                            if manage_acquirers and method_information_mapping[journal_line.payment_method_id.id]['mode'] == 'electronic':
                                protected_acquirer_ids.add(journal_line.payment_acquirer_id.id)

                candidates_acquirer_ids = acquirer_ids - protected_acquirer_ids
                if candidates_acquirer_ids:
                    line.payment_acquirer_id = list(candidates_acquirer_ids)[0]

    def _get_payment_method_domain(self):
        # OVERRIDE
        domain = super()._get_payment_method_domain()
        information = self._get_payment_method_information().get(self.code)

        unique = information.get('mode') == 'unique'
        if unique:
            company_ids = self.env['payment.acquirer'].sudo().search([('provider', '=', self.code)]).mapped('company_id')
            if company_ids:
                domain = expression.AND([domain, [('company_id', 'in', company_ids.ids)]])

        return domain

    @api.ondelete(at_uninstall=False)
    def _unlink_except_active_acquirer(self):
        """ Ensure we don't remove an account.payment.method.line that is linked to an acquirer
        in the test or enabled state.
        """
        active_acquirer = self.payment_acquirer_id.filtered(lambda acquirer: acquirer.state in ['enabled', 'test'])
        if active_acquirer:
            raise UserError(_(
                "You can't delete a payment method that is linked to a provider in the enabled "
                "or test state.\n""Linked providers(s): %s",
                ', '.join(a.display_name for a in active_acquirer),
            ))

    def action_open_acquirer_form(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Acquirer'),
            'view_mode': 'form',
            'res_model': 'payment.acquirer',
            'target': 'current',
            'res_id': self.payment_acquirer_id.id
        }
