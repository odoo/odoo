from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.account.controllers.portal import PortalAccount


class L10nITPortalAccount(PortalAccount):
    def _get_address_errors(self, address_values, *args, **kwargs):
        invalid_fields, missing_fields, error_messages = super()._get_address_errors(
            address_values, *args, **kwargs
        )

        if address_values.get("l10n_it_codice_fiscale"):
            partner_dummy = request.env["res.partner"].new(
                {"l10n_it_codice_fiscale": address_values.get("l10n_it_codice_fiscale")}
            )
            try:
                partner_dummy.check_codice_fiscale()
            except UserError as e:
                invalid_fields.add("l10n_it_codice_fiscale")
                error_messages.append(e.args)

        pa_index = address_values.get("l10n_it_pa_index")
        if pa_index and (len(pa_index) < 6 or len(pa_index) > 7):
            invalid_fields.add("l10n_it_pa_index")
            error_messages.append(
                request.env._(
                    "Destination Code (SDI) must have between 6 and 7 characters."
                )
            )

        return invalid_fields, missing_fields, error_messages
