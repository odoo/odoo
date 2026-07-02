from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_pk_edi_enable = fields.Boolean(compute='_compute_l10n_pk_edi_enable')
    l10n_pk_edi_fbr_customer_status = fields.Selection(
        selection=[
            ('not_checked', "Not Checked"),
            ('registered', "Registered"),
            ('unregistered', "Unregistered"),
        ],
        copy=False,
        default='not_checked',
    )

    @api.depends_context('company')
    def _compute_l10n_pk_edi_enable(self):
        enabled = self.env.company.l10n_pk_edi_enable
        for partner in self:
            partner.l10n_pk_edi_enable = enabled

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

    def _l10n_pk_edi_check_registration(self, vat):
        company = self.env.company
        auth_token = company._get_l10n_pk_edi_auth_token()
        if not auth_token:
            return None
        params = {
            'auth_token': auth_token,
            'json_payload': {'Registration_No': vat},
        }
        return self.env['iap.account']._l10n_pk_connect_to_server(
            not company.sudo().l10n_pk_edi_test_environment,
            params,
            '/api/l10n_pk_edi/1/registration',
        )

    def button_check_fbr_customer_registration(self):
        self.ensure_one()
        if not self.vat:
            self.l10n_pk_edi_fbr_customer_status = 'not_checked'
            return

        response = self._l10n_pk_edi_check_registration(self.vat)
        if not response:
            self.l10n_pk_edi_fbr_customer_status = 'not_checked'
            return
        if response.get('error'):
            raise UserError(response['error'].get('message', _('Unknown error')))

        if reg_type := str(response.get('REGISTRATION_TYPE', '')).lower():
            self.l10n_pk_edi_fbr_customer_status = reg_type
        else:
            self.l10n_pk_edi_fbr_customer_status = 'not_checked'
