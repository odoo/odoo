from odoo.addons.portal.controllers.portal import CustomerPortal


class L10nINCustomerPortal(CustomerPortal):

    def _create_or_update_address(
        self,
        partner_sudo,
        address_type='billing',
        use_delivery_as_billing=False,
        callback='/my/addresses',
        required_fields=False,
        **form_data
    ):
        old_vat = partner_sudo.vat or ''
        partner_sudo, feedback_dict = super()._create_or_update_address(
            partner_sudo,
            address_type=address_type,
            use_delivery_as_billing=use_delivery_as_billing,
            callback=callback,
            required_fields=required_fields,
            **form_data
        )
        if (
            self.env.company.account_fiscal_country_id.code == 'IN'
            and partner_sudo == partner_sudo.commercial_partner_id
            and partner_sudo.country_id.code == 'IN'
            and partner_sudo.vat != old_vat
        ):
            partner_sudo._update_l10n_in_gst_treatment_and_fp_from_iap_autocomplete()
        return partner_sudo, feedback_dict
