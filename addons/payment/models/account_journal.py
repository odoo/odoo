# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.constrains('inbound_payment_method_line_ids')
    def _check_inbound_payment_method_line_ids(self):
        """
        Check and ensure that the user do not remove a apml that is linked to an acquirer in the test or enabled state.
        """
        self.env['account.payment.method'].flush(['code', 'payment_type'])
        self.env['account.payment.method.line'].flush(['payment_method_id'])
        self.env['payment.acquirer'].flush(['provider', 'state'])

        self._cr.execute('''
            SELECT acquirer.id
            FROM payment_acquirer acquirer
            JOIN account_payment_method apm ON apm.code = acquirer.provider
            LEFT JOIN account_payment_method_line apml ON apm.id = apml.payment_method_id
            WHERE acquirer.state IN ('enabled', 'test') AND apm.payment_type = 'inbound'
            AND apml.id IS NULL
        ''')
        ids = [r[0] for r in self._cr.fetchall()]
        acquirers = self.env['payment.acquirer'].browse(ids)
        if acquirers:
            raise UserError(_("You can't delete a payment method that is linked to an acquirer in the enabled or test state.\n"
                              "Linked acquirer(s): %s", ', '.join(a.display_name for a in acquirers)))
