from odoo import fields, models
from odoo.exceptions import UserError


class PajakioRegistrationForm(models.TransientModel):
    _name = "l10n_id_pajakio.registration.form"
    _description = "Pop-up to allow user enter credentials for Pajak.io"

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    mode = fields.Selection(
        selection=[
            ('register_user', "Register User"),
            ('register_company', "Register Company"),
            ('sign_in', "Sign In"),
        ],
        required=True,
    )

    # The fields are combination of user and company registration fields
    email = fields.Char(string="Email", required=True)
    password = fields.Char(
        string="Password",
        required=True,
        help="Password needs to \n - Contain capital letters\n- Contain numbers\n - Contain symbols\n - Be at least 8 characters long",
    )
    user_name = fields.Char(string="Name")
    phone = fields.Char(string="Phone")
    company_name = fields.Char(string="Company Name")
    npwp = fields.Char(string="NPWP", readonly=True)
    address = fields.Char(string="Address")
    city = fields.Char(string="City")

    def action_register_user(self):
        """ Sign-up procedure. Use IAP utility to send request to route /api/pajakio/1/register_user. If successful,
        IAP should return a key_identifier which will be stored on client side.
        """
        payload = {
            "email": self.email,
            "nama": self.user_name,
            "telp": self.phone,
            "password": self.password,
        }
        response = self.env["iap.account"]._l10n_id_pajakio_iap_connect(
            {"reg_payload": payload},
            "/api/pajakio/1/register_user",
            include_key_identifier=False,
        )

        # if error in response, then report the error
        if 'error' in response:
            raise UserError(response.get('error'))

        self.company_id.l10n_id_pajakio_email = self.email
        self.company_id._l10n_id_pajakio_set_key_identifier(response.get('data', {}).get('key_identifier'))
        return self.company_id._l10n_id_pajakio_action_register_company()

    def action_register_company(self):
        """ Company registration procedure. Can only be run once user is registered. """
        payload = {
            "email": self.email,
            "password": self.password,
            "npwp": self.npwp,
            "nama": self.company_name,
            "alamat": self.address,
            "kota": self.city,
            "partnerCode": "ODOO",  # fixed argument for Pajak.io team to identify our account as Odoo partner
        }
        response = self.env["iap.account"]._l10n_id_pajakio_iap_connect(
            {"reg_payload": payload},
            "/api/pajakio/1/register_company",
        )

        # if error in response, report the error
        if 'error' in response:
            raise UserError(response.get('error'))

        self.company_id.l10n_id_pajakio_company_registered = True
        self.company_id._l10n_id_pajakio_activate()

    def action_sign_in(self):
        """ If pajak.io account is already created outside Odoo, user can sign ing with email-password-npwp"""

        payload = {
            "email": self.email,
            "password": self.password,
            "npwp": self.npwp,
        }

        response = self.env["iap.account"]._l10n_id_pajakio_iap_connect(
            {"payload": payload},
            "/api/pajakio/1/sign_in",
            include_key_identifier=False,
        )

        # if error in response, report the error
        # else save key_identifier
        if 'error' in response:
            raise UserError(self.env._("Sign in failed: %(error)s", error=response.get('error')))

        self.company_id.l10n_id_pajakio_email = self.email
        self.company_id._l10n_id_pajakio_set_key_identifier(response.get('data', {}).get('key_identifier'))
        self.company_id.l10n_id_pajakio_company_registered = True

        self.company_id._l10n_id_pajakio_activate()
