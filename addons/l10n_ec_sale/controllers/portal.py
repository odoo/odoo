# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.l10n_latam_base.controllers.portal import L10nLatamBasePortalAccount


class L10nECSalePortalAccount(L10nLatamBasePortalAccount):

    def _get_payment_values(self, order, **kwargs):
        payment_form_values = super()._get_payment_values(order, **kwargs)
        company = order.company_id
        # Do not show payment methods without l10n_ec_sri_payment_id. Payment methods without this
        # fields could cause issues since we require a l10n_ec_sri_payment_id to post a move.
        if company.account_fiscal_country_id.code == 'EC':
            payment_methods = payment_form_values['payment_methods_sudo'].filtered(
                lambda pm: bool(pm.l10n_ec_sri_payment_id)
            )
            payment_form_values['payment_methods_sudo'] = payment_methods
        return payment_form_values

