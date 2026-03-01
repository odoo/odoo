from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    # -------------------------------------------------------------------------
    # Validation Methods
    # -------------------------------------------------------------------------
    l10n_pk_edi_fbr_customer_status = fields.Selection(
        selection=[
            ('not_checked', "Not Checked"),
            ('registered', "Registered"),
            ('unregistered', "Unregistered"),
        ],
        string="FBR Registration Status",
        copy=False,
        default='not_checked',
    )

    def _l10n_pk_edi_is_valid_vat(self):
        self.ensure_one()
        if not self.vat:
            return False
        return len(self.vat) == 7 or len(self.vat) == 13

    def _group_by_error_code(self):
        self.ensure_one()
        if not all(self[field] for field in ("street", "city", "state_id", "country_id")):
            return (
                ("message", self.env._("Partner(s) should have a complete address, verify their Street, City, State and Country.")),
                ("error_code", "l10n_pk_edi_partner_address_missing"),
                ("level", "danger"),
            )
        if self.l10n_pk_edi_fbr_customer_status == 'not_checked':
            return (
                ("message", self.env._("The FBR Registration Status for '%s' is not checked. Please verify their status before proceeding.", self.display_name)),
                ("error_code", "l10n_pk_edi_partner_fbr_status_not_checked"),
                ("level", "danger"),
            )
        return False

    def _l10n_pk_edi_export_check(self):
        """Validate Partner for E-Invoicing compliance."""
        alert_vals = {}
        for error_tuple, invalid_records in self.grouped(lambda m: m._group_by_error_code()).items():
            if not error_tuple:
                continue
            temp_dict = dict(error_tuple)
            alert_vals.update(
                {
                    temp_dict["error_code"]: {
                        "message": temp_dict["message"],
                        "level": temp_dict["level"],
                        "action": invalid_records._get_records_action(),
                        "action_text": self.env._("View Partner(s)"),
                    },
                },
            )
        return alert_vals

    def check_fbr_customer_registration(self):
        self.ensure_one()
        if not self.vat:
            self.l10n_pk_edi_fbr_customer_status = 'not_checked'
            return

        company = self.env.company
        auth_token = company.l10n_pk_edi_auth_token
        if not auth_token:
            # Optionally log a warning or use your _l10n_pk_edi_compose_error_response here
            self.l10n_pk_edi_fbr_customer_status = 'not_checked'
            return

        is_production = not company.sudo().l10n_pk_edi_test_environment
        params = {
            'auth_token': auth_token,
            'json_payload': {'Registration_No': self.vat},
        }

        response = self.env['iap.account']._l10n_pk_connect_to_server(
            is_production,
            params,
            '/api/l10n_pk_edi/1/registration',
        )

        if not response:
            self.l10n_pk_edi_fbr_customer_status = 'not_checked'
            return

        # Mapping based on FBR Web Method 5.12 specs
        # statuscode: "00" (Success/Registered), "01" (Unregistered)
        if reg_type := str(response.get('REGISTRATION_TYPE', '')).lower():
            self.l10n_pk_edi_fbr_customer_status = reg_type
        else:
            # Fallback if the API returns an error or unknown status
            self.l10n_pk_edi_fbr_customer_status = 'not_checked'
