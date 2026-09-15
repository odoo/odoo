from odoo.libs.debug_log import DebugLog

from odoo.addons.l10n_latam_base.controllers.portal import L10nLatamBasePortalAccount

_debug = DebugLog(__name__)


class L10nECSalePortalAccount(L10nLatamBasePortalAccount):
    def _prepare_payment_form_context(self, order, **kwargs):
        payment_form_values = super()._prepare_payment_form_context(order, **kwargs)
        company = order.company_id
        # Do not show payment methods without l10n_ec_sri_payment_id. Payment methods without this
        # fields could cause issues since we require a l10n_ec_sri_payment_id to post a move.
        if company.account_fiscal_country_id.code == "EC":
            payment_methods = payment_form_values["payment_methods_sudo"].filtered(
                lambda pm: bool(pm.l10n_ec_sri_payment_id)
            )
            _debug.logic(
                "sri_payment_methods_filtered",
                order=order,
                before=payment_form_values["payment_methods_sudo"],
                after=payment_methods,
            )
            payment_form_values["payment_methods_sudo"] = payment_methods
        return payment_form_values
