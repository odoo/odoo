from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_id_pajakio_mode = fields.Selection(
        string="Pajak.io Integration Mode",
        help="Mode of operation for Pajak.io integration. Will affect the URL path of API requests",
        related="company_id.l10n_id_pajakio_mode",
        readonly=False,
    )
    l10n_id_pajakio_active = fields.Boolean(
        related="company_id.l10n_id_pajakio_active",
        readonly=False,
    )
    l10n_id_pajakio_email = fields.Char(
        related="company_id.l10n_id_pajakio_email",
    )

    # compute fields to control invisiblity of buttons
    l10n_id_pajakio_show_register_user = fields.Boolean(compute="_compute_l10n_id_pajakio_show_buttons")
    l10n_id_pajakio_show_register_company = fields.Boolean(compute="_compute_l10n_id_pajakio_show_buttons")
    l10n_id_pajakio_show_activate_service = fields.Boolean(compute="_compute_l10n_id_pajakio_show_buttons")
    l10n_id_pajakio_show_deactivate_service = fields.Boolean(compute="_compute_l10n_id_pajakio_show_buttons")

    def action_pajakio_register_user(self):
        """ Open the registration wizard for user to input their credentials to register in Pajak.io """
        return self.company_id._l10n_id_pajakio_action_register_user()

    def action_pajakio_register_company(self):
        """ Open registration wizard for company to input their credentials to register in Pajak.io """
        return self.company_id._l10n_id_pajakio_action_register_company()

    def action_activate_pajakio_service(self):
        """ Once email and key_identifier is setup on IAP server """
        self.company_id._l10n_id_pajakio_activate()

    def action_sign_in_pajakio(self):
        """ Open wizard to let user input email, password and NPWP to sign in pajak.io """
        return self.company_id._l10n_id_pajakio_action_sign_in()

    def action_logout_pajakio(self):
        """ Log out of Pajak.io locally: deactivate the integration and clear the
        stored credentials for the current mode. The proxy key and its free credits remain
        active in case user logs into that company again in the future. """
        self.company_id._l10n_id_pajakio_logout()

    @api.depends('company_id.l10n_id_pajakio_email', 'company_id.l10n_id_pajakio_company_registered', 'company_id.l10n_id_pajakio_active')
    def _compute_l10n_id_pajakio_show_buttons(self):
        """ Register user should only be shown if the email is not set up yet. Rule for register user should be the same as sign in
            Register company should only be shown if the email is setup and the company isn't registered yet
        """
        for record in self:
            email = record.company_id.l10n_id_pajakio_email
            company_registered = record.company_id.l10n_id_pajakio_company_registered

            record.l10n_id_pajakio_show_register_user = not bool(email)
            record.l10n_id_pajakio_show_register_company = bool(email) and not company_registered
            record.l10n_id_pajakio_show_activate_service = company_registered and not bool(record.company_id.l10n_id_pajakio_active)
            record.l10n_id_pajakio_show_deactivate_service = bool(record.company_id.l10n_id_pajakio_active)
