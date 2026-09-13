import re

from odoo import fields, models
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_id_pajakio_mode = fields.Selection(
        string="Pajak.io Integration Mode",
        selection=[
            ("test", "Test"),
            ("prod", "Production"),
        ],
        default="test",
    )
    l10n_id_pajakio_active = fields.Boolean()

    l10n_id_pajakio_key_identifier = fields.Char(string="Pajak.io Key Identifier", groups=fields.NO_ACCESS)
    l10n_id_pajakio_email = fields.Char(string="Pajak.io User Email")
    l10n_id_pajakio_company_registered = fields.Boolean()

    def _l10n_id_pajakio_action_register_user(self):
        """ Open the registration wizard for user to input their credentials to register in Pajak.io """
        self.ensure_one()
        # clean up the format of the phone that is eligible for registration
        national_phone = self._phone_format(
            number=self.phone,
            force_format='NATIONAL',
        )
        sanitized_phone = re.sub(r'\D', '', national_phone) if national_phone else False
        return {
            "type": "ir.actions.act_window",
            "name": "User Registration",
            "res_model": "l10n_id_pajakio.registration.form",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_mode": "register_user",
                "default_company_id": self.id,
                "default_email": self.email,
                "default_user_name": self.env.user.name,
                "default_phone": sanitized_phone,
                "dialog_size": "medium",
            },
        }

    def _l10n_id_pajakio_action_register_company(self):
        """ Open registration wizard for company to input their credentials to register in Pajak.io """
        self.ensure_one()
        # can only register if the user email is configured
        email = self.l10n_id_pajakio_email
        if not email:
            raise UserError(self.env._("Please register your user account first before registering your company."))

        return {
            "type": "ir.actions.act_window",
            "name": "Company Registration",
            "res_model": "l10n_id_pajakio.registration.form",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_mode": "register_company",
                "default_company_id": self.id,
                "default_email": email,
                "default_npwp": self.vat,
                "dialog_size": "medium",
            },
        }

    def _l10n_id_pajakio_action_sign_in(self):
        """ Open wizard to let user input email, password and NPWP to sign in pajak.io """
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Sign In",
            "res_model": "l10n_id_pajakio.registration.form",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_mode": "sign_in",
                "default_company_id": self.id,
                "default_email": self.email,
                "default_npwp": self.vat,
                "dialog_size": "medium",
            },
        }

    def _l10n_id_pajakio_logout(self):
        """ Log out of Pajak.io locally: deactivate the integration and clear the
        stored credentials for the current mode. The proxy key and its free credits remain
        active in case user logs into that company again in the future. """
        self.ensure_one()
        self._l10n_id_pajakio_activate(status=False)
        self.l10n_id_pajakio_email = False
        self._l10n_id_pajakio_set_key_identifier(False)
        self.l10n_id_pajakio_company_registered = False

    def _l10n_id_pajakio_get_data(self):
        """ Get email, key_identifier and mode """
        return self.l10n_id_pajakio_mode, self.sudo().l10n_id_pajakio_key_identifier, self.l10n_id_pajakio_email

    def _l10n_id_pajakio_set_key_identifier(self, key_identifier):
        self.sudo().l10n_id_pajakio_key_identifier = key_identifier

    def _l10n_id_pajakio_activate(self, status=True):
        """ Toggle the local `l10n_id_pajakio_active` flag.

        status=True: also registers with the proxy over IAP (fetches the API key).
        status=False: local-only - flips the flag off without contacting the proxy,
        so the proxy-side key and its free-credit pool remain untouched. """
        self.ensure_one()
        if self.l10n_id_pajakio_active == status:
            return

        # force Pajak.io iap.account to be created
        self.env['iap.account'].get('l10n_id_pajakio_proxy')

        # make sure email and key_identifier is configured
        _mode, key_identifier, email = self._l10n_id_pajakio_get_data()
        if not (key_identifier and email):
            raise UserError(self.env._("No Pajak.io account has been configured for this database yet. Please register or sign in"))

        # for registration only
        if status:
            response = self.env['iap.account']._l10n_id_pajakio_iap_connect(
                {},
                "/api/pajakio/1/register",
            )

            # report error and set the company to have activated pajakio
            if 'error' in response:
                raise UserError(self.env._("Pajak.io service activation failed: %(error)s", error=response.get('error')))

        self.l10n_id_pajakio_active = status
