# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PaymentToken(models.Model):
    _name = 'payment.token'
    _inherit = 'payment.token'

    def _handle_archiving(self):
        """ Override of payment to void the token on linked subscriptions.

        :return: None
        """
        super()._handle_archiving()

        linked_subscriptions = self.env['sale.order'].search([('payment_token_id', 'in', self.ids)])
        linked_subscriptions.write({'payment_token_id': None})

    def _get_available_tokens(self, providers_ids, partner_id, is_subscription=False, **kwargs):
        """ Override of `payment` to include the commercial partners' tokens.

        :param list providers_ids: The ids of the providers available for the transaction.
        :param int partner_id: The id of the partner.
        :param bool is_subscription: Whether the order is a subscription.
        :param dict kwargs: Locally unused keywords arguments.
        :return: The available tokens.
        :rtype: payment.token
        """
        if not is_subscription:
            return super()._get_available_tokens(providers_ids, partner_id, **kwargs)

        partner = self.env['res.partner'].browse(partner_id)
        return self.env['payment.token'].sudo().search([
            ('provider_id', 'in', providers_ids),
            ('partner_id', 'child_of', partner.commercial_partner_id.id),
        ])  # In sudo mode to read fields of the children of the commercial partner.

    def get_linked_records_info(self):
        """ Override of payment to add information about subscriptions linked to the current token.

        Note: self.ensure_one()

        :return: The list of information about linked subscriptions
        :rtype: list
        """
        res = super().get_linked_records_info()
        subscriptions = self.env['sale.order'].search([('payment_token_id', '=', self.id)])
        for sub in subscriptions:
            res.append({
                'description': subscriptions._description,
                'id': sub.id,
                'name': sub.name,
                'url': sub.get_portal_url(),
                'active_subscription': sub.subscription_state in ['3_progress', '4_paused'],
            })
        return res
