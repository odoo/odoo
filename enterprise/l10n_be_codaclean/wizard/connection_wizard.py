from odoo import _, api, fields, models
from odoo.addons.l10n_be_codaclean.tools.iap_api import get_error_message


class L10nBeCodacleanConnectionWizard(models.TransientModel):
    _name = 'l10n_be_codaclean.connection.wizard'
    _description = 'Codaclean Connection Wizard'
    _check_company_auto = True

    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    codaclean_is_connected = fields.Boolean(
        related='company_id.l10n_be_codaclean_is_connected',
    )
    username = fields.Char(
        string="Login",
    )
    password = fields.Char(
        string="Password",
        groups='base.group_system',
    )
    iap_token = fields.Char(
        related='company_id.l10n_be_codaclean_iap_token',
        readonly=True,
    )
    iap_connection_exists = fields.Boolean(
        string="IAP Connection Exists",
        compute="_compute_iap_connection_exists",
    )
    warning = fields.Char(
        string="Warning",
        readonly=True,
    )

    @api.depends("company_id")
    def _compute_iap_connection_exists(self):
        for wizard in self:
            wizard.iap_connection_exists = bool(wizard.company_id.l10n_be_codaclean_iap_token)

    def _action_open(self):
        self.password = False
        return self._get_records_action(name=_("Manage Connection"), target='new')

    def l10n_be_codaclean_connect(self):
        self.ensure_one()
        result = self.company_id._l10n_be_codaclean_connect(self.username, self.password)
        error = result.get("error")
        self.warning = get_error_message(error) if error else False
        return self._action_open()

    def refresh_connection_status(self):
        self.ensure_one()
        result = self.company_id._l10n_be_codaclean_check_status()
        error = result.get("error")
        self.warning = get_error_message(error) if error else False
        return self._action_open()

    def l10n_be_codaclean_change_credentials(self):
        self.ensure_one()
        result = self.company_id._l10n_be_codaclean_change_credentials(self.username, self.password)
        error = result.get("error")
        self.warning = get_error_message(error) if error else False
        return self._action_open()

    def l10n_be_codaclean_disconnect(self):
        self.ensure_one()
        result = self.company_id._l10n_be_codaclean_disconnect()
        error = result.get("error")
        self.warning = get_error_message(error) if error else False
        return self._action_open()
