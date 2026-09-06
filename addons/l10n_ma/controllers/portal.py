from odoo.addons.account.controllers.portal import PortalAccount


class L10nMAPortalAccount(PortalAccount):

    def _is_morocco_fiscal_country(self):
        return self.env.company.account_fiscal_country_id.code == "MA"

    def _get_checkout_additional_identifiers_metadata(self, country_code):
        metadata = super()._get_checkout_additional_identifiers_metadata(country_code)
        # The ICE has its own field on the address form.
        metadata.pop('MA_ICE', None)
        return metadata

    def _prepare_address_form_values(self, *args, **kwargs):
        rendering_values = super()._prepare_address_form_values(*args, **kwargs)
        if rendering_values["country"].code != "MA" and not self._is_morocco_fiscal_country():
            return rendering_values

        current_partner = rendering_values["current_partner"]
        current_ice = current_partner and current_partner._get_additional_identifier("MA_ICE")
        ice_warning = ""
        if current_ice and not rendering_values["can_edit_commercial_fields"]:
            ice_warning = self.env._(
                "Modifying the ICE number is not allowed once documents have been issued for your"
                " account. Please contact us directly if that's what you intend to do."
            )

        return {
            **rendering_values,
            "current_ice": current_ice,
            "ice_warning": ice_warning,
        }
