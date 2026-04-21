from odoo import _, fields, models
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = "res.company"

    # =============== Pajak.io Integration Related Fields ===============
    l10n_id_pajakio_mode = fields.Selection(
        string="Pajak.io Integration Mode",
        selection=[
            ("test", "Test"),
            ("prod", "Production")
        ],
        default="prod",
    )
    l10n_id_pajakio_active = fields.Boolean(default=False)

    l10n_id_pajakio_client_id = fields.Char(string="Pajak.io Client ID")
    l10n_id_pajakio_email = fields.Char(string="Pajak.io User Email")

    l10n_id_pajakio_test_client_id = fields.Char(string="Pajak.io Test Client ID")
    l10n_id_pajakio_test_email = fields.Char(string="Pajak.io Test User Email")

    def _l10n_id_pajakio_get_data(self):
        """ Get email client_id and mode depending on the mode setup"""
        if self.l10n_id_pajakio_mode == "prod":
            email = self.l10n_id_pajakio_email
            client_id = self.l10n_id_pajakio_client_id
        else:
            email = self.l10n_id_pajakio_test_email
            client_id = self.l10n_id_pajakio_test_client_id
        return self.l10n_id_pajakio_mode, client_id, email

    def _l10n_id_pajakio_set_email(self, email):
        if self.l10n_id_pajakio_mode == "prod":
            self.l10n_id_pajakio_email = email
        else:
            self.l10n_id_pajakio_test_email = email

    def _l10n_id_pajakio_set_client_id(self, client_id):
        if self.l10n_id_pajakio_mode == "prod":
            self.l10n_id_pajakio_client_id = client_id
        else:
            self.l10n_id_pajakio_test_client_id = client_id

    def _l10n_id_pajakio_activate(self, status=True):
        """ Activate pajak.io connection by setting active to True. This will be called once registration is successful"""
        # Avoid unnecessary calls when the company is already in the desired state.
        if self.l10n_id_pajakio_active == status:
            return

        # force Pajak.io iap.account to be created
        self.env['iap.account'].get('l10n_id_pajakio_proxy')

        # make sure email and client_id is configured
        mode, client_id, email = self._l10n_id_pajakio_get_data()
        if not (client_id and email):
            raise UserError(_("No Pajak.io account has been configured for this database yet. Please register or sign in"))

        # Do actual registration
        params = {
            "client_id": client_id
        }
        route = "/api/pajakio/1/register" if status else "/api/pajakio/1/unregister"
        response = self.env['iap.account']._l10n_id_pajakio_iap_connect(
            params,
            route,
        )

        # report error and set the company to have activated pajakio
        if 'error' in response:
            raise UserError(_("Pajak.io service activation failed: %s", response.get('error')))

        self.l10n_id_pajakio_active = status
