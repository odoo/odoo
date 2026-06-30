from odoo import _, fields, models, api
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # =============== Pajak.io Integration Related Fields ===============
    l10n_id_pajakio_mode = fields.Selection(
        string="Pajak.io Integration Mode",
        help="Mode of operation for Pajak.io integration. Will affect the URL path of API requests",
        related="company_id.l10n_id_pajakio_mode",
        readonly=False
    )
    l10n_id_pajakio_active = fields.Boolean(
        related="company_id.l10n_id_pajakio_active",
        readonly=False
    )

    l10n_id_pajakio_client_id = fields.Char(
        string="Pajak.io Client ID",
        related='company_id.l10n_id_pajakio_client_id',
        readonly=False
    )
    l10n_id_pajakio_email = fields.Char(
        string="Pajak.io User Email",
        related="company_id.l10n_id_pajakio_email",
        readonly=False
    )

    l10n_id_pajakio_test_client_id = fields.Char(
        string="Pajak.io Test Client ID",
        related="company_id.l10n_id_pajakio_test_client_id"
    )
    l10n_id_pajakio_test_email = fields.Char(
        string="Pajak.io Test User Email",
        related="company_id.l10n_id_pajakio_test_email"
    )

    # compute fields to control invisiblity of buttons
    l10n_id_pajakio_show_register_user = fields.Boolean(compute="_compute_l10n_id_pajakio_show_buttons")
    l10n_id_pajakio_show_register_company = fields.Boolean(compute="_compute_l10n_id_pajakio_show_buttons")
    l10n_id_pajakio_show_activate_service = fields.Boolean(compute="_compute_l10n_id_pajakio_show_buttons")
    l10n_id_pajakio_show_deactivate_service = fields.Boolean(compute="_compute_l10n_id_pajakio_show_buttons")

    def action_pajakio_register_user(self):
        """ Open the registration wizard for user to input their credentials to register in Pajak.io """
        return {
            "type": "ir.actions.act_window",
            "name": "Pajak.io User Registration",
            "res_model": "l10n_id_pajakio.registration.form",
            "view_mode": "form",
            "target": "new",
            "context": {
                "register_user": True,
                "default_email": self.env.company.email,
                "default_user_name": self.env.user.name,
                "default_phone": self.env.user.phone
            }
        }

    def action_pajakio_register_company(self):
        """ Open registration wizard for company to input their credentials to register in Pajak.io """
        # can only regiser if the user email is configuredL
        email = self.env.company.l10n_id_pajakio_email if self.l10n_id_pajakio_mode == "prod" else self.env.company.l10n_id_pajakio_test_email
        if not email:
            raise UserError(_("You have not signed in or registered user"))

        return {
            "type": "ir.actions.act_window",
            "name": "Pajak.io Company Registration",
            "res_model": "l10n_id_pajakio.registration.form",
            "view_mode": "form",
            "target": "new",
            "context": {
                "register_company": True,
                "default_email": email,
                "default_npwp": self.env.company.vat
            }
        }

    def action_activate_pajakio_service(self):
        """ Once email and client_id is setup on IAP server """
        self.company_id._l10n_id_pajakio_activate()

    def action_deactivate_pajakio_service(self):
        """ Deactivate pajak.io service by setting active to False """
        self.company_id._l10n_id_pajakio_activate(status=False)

    def action_sign_in_pajakio(self):
        """ Open wizard to let user input email, password and NPWP to sign in pajak.io """
        return {
            "type": "ir.actions.act_window",
            "name": "Pajak.io Sign In",
            "res_model": "l10n_id_pajakio.registration.form",
            "view_mode": "form",
            "target": "new",
            "context": {
                "sign_in": True,
                "default_email": self.env.company.email,
                "default_npwp": self.env.company.vat
            }
        }

    @api.depends('company_id.l10n_id_pajakio_email', 'company_id.l10n_id_pajakio_client_id', 'company_id.l10n_id_pajakio_test_email', 'company_id.l10n_id_pajakio_test_client_id', 'l10n_id_pajakio_mode')
    def _compute_l10n_id_pajakio_show_buttons(self):
        """ Register user should only be shown if the email is not set up yet. Rule for register user should be the same as sign in
            Register company should only be shown if the email is setup and no client_id is setup yet
        """
        if self.l10n_id_pajakio_mode == "prod":
            email = self.env.company.l10n_id_pajakio_email
            client_id = self.env.company.l10n_id_pajakio_client_id
        else:
            email = self.env.company.l10n_id_pajakio_test_email
            client_id = self.env.company.l10n_id_pajakio_test_client_id

        self.l10n_id_pajakio_show_register_user = not bool(email)
        self.l10n_id_pajakio_show_register_company = bool(email) and not bool(client_id)
        self.l10n_id_pajakio_show_activate_service = bool(client_id) and not bool(self.env.company.l10n_id_pajakio_active)
        self.l10n_id_pajakio_show_deactivate_service = bool(self.env.company.l10n_id_pajakio_active)
