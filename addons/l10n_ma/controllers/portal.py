from odoo.addons.account.controllers.portal import PortalAccount


class L10nMAPortalAccount(PortalAccount):

    def _get_checkout_additional_identifiers_metadata(self, country_code):
        metadata = super()._get_checkout_additional_identifiers_metadata(country_code)
        # The ICE has its own field on the address form.
        metadata.pop('MA_ICE', None)
        return metadata
