# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    pos_payment_method_id = fields.Many2one('pos.payment.method', "POS Payment Method")
    force_outstanding_account_id = fields.Many2one("account.account", "Forced Outstanding Account", check_company=True)
    pos_session_id = fields.Many2one('pos.session', "POS Session", index='btree_not_null')

    @api.depends("force_outstanding_account_id")
    def _compute_outstanding_account_id(self):
        """When force_outstanding_account_id is set, we use it as the outstanding_account_id."""
        super()._compute_outstanding_account_id()
        for payment in self:
            if payment.force_outstanding_account_id:
                payment.outstanding_account_id = payment.force_outstanding_account_id

    def _get_payment_method_codes_to_exclude(self):
        res = super()._get_payment_method_codes_to_exclude()

        # Sepa Credit Transfer is an outgoing payment method. It requires a partner and bank
        # account. In the context of PoS orders, you can make refunds that are not linked to
        # a specific customer. We ensure that account.payment are not created using the sepa_ct
        # account.payment.method.line. If not, closing the session would not be possible unless
        # having an account.payment.method.line with a smaller sequence than sepa_ct.
        account_sepa = self.env['ir.module.module'].search([('name', '=', 'account_iso20022')])
        if account_sepa.state == 'installed':
            sepa_ct = self.env.ref('account_iso20022.account_payment_method_sepa_ct', raise_if_not_found=False)
            if sepa_ct and 'pos_payment' in self.env.context and sepa_ct.code not in res:
                res.append(sepa_ct.code)
        return res
