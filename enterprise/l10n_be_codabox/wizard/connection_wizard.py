import requests
from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.addons.l10n_be_codabox.const import get_error_msg


class L10nBeCodaBoxConnectionWizard(models.TransientModel):
    _name = 'l10n_be_codabox.connection.wizard'
    _description = 'CodaBox Connection Wizard'
    _check_company_auto = True

    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    company_vat = fields.Char(
        string='Company VAT/ID',
        compute='_compute_company_vat',
        readonly=True,
    )
    fiduciary_vat = fields.Char(
        string='Accounting Firm VAT',
        related='company_id.l10n_be_codabox_fiduciary_vat',
    )
    l10n_be_codabox_is_connected = fields.Boolean(related='company_id.l10n_be_codabox_is_connected')
    fidu_password = fields.Char(
        string='Password',
        help='This is the password you have received from Odoo the first time you connected to CodaBox.'
             ' Check the documentation if you have forgotten your password.',
        groups="base.group_system",
    )
    show_fidu_password = fields.Boolean(compute='_compute_show_fidu_password')
    nb_connections = fields.Integer()
    connection_exists = fields.Boolean()
    is_fidu_consent_valid = fields.Boolean()

    def _compute_company_vat(self):
        for wizard in self:
            wizard.company_vat = wizard.company_id.l10n_be_codabox_company_vat

    def _compute_show_fidu_password(self):
        for wizard in self:
            wizard.show_fidu_password = (
                wizard.nb_connections > 0
                and wizard.is_fidu_consent_valid
                and not wizard.l10n_be_codabox_is_connected
            )

    def do_nothing(self):
        self.fidu_password = False
        return self.company_id._l10n_be_codabox_return_wizard(
            name=_('Manage Connection'),
            view_id=False,
            res_model='l10n_be_codabox.connection.wizard',
            res_id=self.id,
        )

    def l10n_be_codabox_create_connection(self):
        self.ensure_one()
        self.company_id._l10n_be_codabox_verify_prerequisites()
        try:
            params = self.company_id._l10n_be_codabox_get_iap_common_params()
            params["fidu_password"] = self.fidu_password
            params["callback_url"] = self.get_base_url()
            result = self.company_id._l10_be_codabox_call_iap_route("connect", params)
            if result.get("iap_token"):  # First and following connection
                self.company_id.l10n_be_codabox_iap_token = result["iap_token"]
            if result.get("fidu_password") and result.get("confirmation_url"):
                # Show the wizard with the confirmation URL button and the generated fiduciary password
                wizard = self.env['l10n_be_codabox.validation.wizard'].create({
                    'company_id': self.company_id.id,
                    'fidu_password': result["fidu_password"],
                    'confirmation_url': result["confirmation_url"],
                })
                return self.company_id._l10n_be_codabox_return_wizard(
                    name=_('Connection Validation'),
                    view_id=self.env.ref('l10n_be_codabox.validation_wizard_view').id,
                    res_model='l10n_be_codabox.validation.wizard',
                    res_id=wizard.id,
                )
            return self.refresh_connection_status()
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise UserError(get_error_msg({"type": "error_connecting_iap"}))
        finally:
            self.fidu_password = False

    def l10n_be_codabox_open_change_password_wizard(self):
        wizard = self.env['l10n_be_codabox.change.password.wizard'].create({
            'company_id': self.company_id.id,
        })
        return self.company_id._l10n_be_codabox_return_wizard(
            name=_('Change password'),
            view_id=self.env.ref('l10n_be_codabox.validation_wizard_view').id,
            res_model='l10n_be_codabox.change.password.wizard',
            res_id=wizard.id,
        )

    def refresh_connection_status(self):
        self.company_id._l10n_be_codabox_refresh_connection_status()
        return self.do_nothing()

    def l10n_be_codabox_revoke(self):
        self.company_id._l10n_be_codabox_verify_prerequisites()
        try:
            params = self.company_id._l10n_be_codabox_get_iap_common_params()
            params["iap_token"] = self.company_id.l10n_be_codabox_iap_token
            self.company_id._l10_be_codabox_call_iap_route("revoke", params)
            self.company_id.l10n_be_codabox_iap_token = False
            self.company_id.l10n_be_codabox_is_connected = False
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'info',
                    'title': _('Information'),
                    'message': _('CodaBox connection revoked.'),
                    'next': {
                        'type': 'ir.actions.act_window_close'
                    },
                }
            }
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise UserError(get_error_msg({"type": "error_connecting_iap"}))
