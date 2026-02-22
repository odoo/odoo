# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Everything is put under config parameter because we want to make user each database
    # is associated with just 1 pajak.io account
    l10n_id_pajakio_mode = fields.Selection(
        [
            ("test", "Testing"),
            ("prod", "Production")
        ],
        default="test",
        config_parameter="l10n_id_pajakio.mode",
        string="Pajak.io operation mode"
    )
    l10n_id_pajakio_test_client_id = fields.Char(
        config_parameter="l10n_id_pajakio.test_client_id",
        string="Pajak.io Client ID",
        help="Client ID is stored which later on can retrieve API key and store it on IAP server",
    )
    l10n_id_pajakio_client_id = fields.Char(
        config_parameter="l10n_id_pajakio.client_id",
        string="Pajak.io Client ID",
    )

    # Test and Production account credential
    l10n_id_pajakio_test_email = fields.Char(string="Pajak.io Testing Account Email", config_parameter="l10n_id_pajakio.test_email")
    l10n_id_pajakio_test_password = fields.Char(string="Pajak.io Testing Account Password", config_parameter="l10n_id_pajakio.test_password")

    l10n_id_pajakio_email = fields.Char(string="Pajak.io Production Account Email", config_parameter="l10n_id_pajakio.email")
    l10n_id_pajakio_password = fields.Char(string="Pajak.io Production Account Password", config_parameter="l10n_id_pajakio.password")

    l10n_id_pajakio_hide_register = fields.Boolean(
        string="Hide Production Account Registration",
        help="If you have already registered a Pajak.io production account, you can hide the registration button",
        compute="_compute_l10n_id_pajakio_register_button"
    )
    l10n_id_pajakio_hide_register_company = fields.Boolean(
        compute="_compute_l10n_id_pajakio_register_button"
    )
    l10n_id_pajakio_active = fields.Boolean(
        help="Whether the Pajak.io service is being activated or not",
        config_parameter="l10n_id_pajakio.active",
        default=False
    )

    l10n_id_pajakio_linked = fields.Boolean(
        compute="_compute_l10n_id_pajakio_linked"
    )

    def action_sign_in_pajakio(self):
        """ If user already has an account, they can sign in and retrieve the Client ID, which
         we can continue with action_link_company_iap """
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_id_pajakio.signin',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_npwp': self.env.company.vat or ''},
        }


    def action_register_user_pajakio(self):
        """ Return the wizard screen to allow user register a Pajak.io user account"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_id_pajakio.register.user',
            'view_mode': 'form',
            'target': 'new',
        }

    
    def action_register_company_pajakio(self):
        """ return wizard screen to allow company registration, carrying email and password
        information from the previous"""

        mode = self.env['ir.config_parameter'].sudo().get_param('l10n_id_pajakio.mode')
        email = self.l10n_id_pajakio_test_email if mode == "test" else self.l10n_id_pajakio_email
        password = self.l10n_id_pajakio_test_password if mode == "test" else self.l10n_id_pajakio_password

        ctx = {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_id_pajakio.register.company',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_email': email,
                'default_password': password,
                'default_npwp': self.env.company.vat,
            }
        }
        return ctx
    
    def action_link_company_iap(self):
        """ Call the registration """
        # Force to create IAP account of Pajak.io before actually handling the service
        account_id = self.env['iap.account'].get_account_id("l10n_id_pajakio_proxy")

        mode = self.env['ir.config_parameter'].sudo().get_param('l10n_id_pajakio.mode')
        client_id = self.env['ir.config_parameter'].get_param('l10n_id_pajakio.test_client_id') if mode == "test" else self.env['ir.config_parameter'].get_param('l10n_id_pajakio.client_id')
        if not client_id:
            raise ValidationError(_("Pajak.io: Cannot link Pajak.io service because Client ID is not found. Please register your company first."))
        params = {
            "client_id": client_id
        }
        result = self.env['iap.account']._l10n_id_pajakio_iap_connect(
            params,
            "/l10n_id_pajakio/register",
        )
        if message := result.get('error'):
            raise ValidationError(_(message))
        
        # when no error is encountered, activate l10n_id_pajakio.active
        self.env['ir.config_parameter'].sudo().set_param('l10n_id_pajakio.active', True)
    
    def action_unlink_company_iap(self):
        """ Deactivate pajak.io services by sending cancel request to IAP server """

        mode = self.env['ir.config_parameter'].sudo().get_param('l10n_id_pajakio.mode')
        client_id = self.env['ir.config_parameter'].get_param('l10n_id_pajakio.test_client_id') if mode == "test" else self.env['ir.config_parameter'].get_param('l10n_id_pajakio.client_id')
        params = {"client_id": client_id}
        result = self.env['iap.account']._l10n_id_pajakio_iap_connect(
            params,
            "/l10n_id_pajakio/unregister",
        )
        if message := result.get('error'):
            raise ValidationError(_(message))
        
        # when no error is encountered, deactivate l10n_id_pajakio.active
        self.env['ir.config_parameter'].sudo().set_param('l10n_id_pajakio.active', False)
    
    def _compute_l10n_id_pajakio_register_button(self):
        """
        register user should show when email password is not set yet => invisible when both are set
        register company should show when email password is set but no client id yet = invisible when 
        """

        config_param = self.env['ir.config_parameter'].sudo()
        mode = config_param.get_param('l10n_id_pajakio.mode')
        for record in self:
            if mode == "test":
                record.l10n_id_pajakio_hide_register = bool(config_param.get_param('l10n_id_pajakio.test_email') and config_param.get_param('l10n_id_pajakio.test_password'))
                record.l10n_id_pajakio_hide_register_company = not record.l10n_id_pajakio_hide_register or bool(config_param.get_param('l10n_id_pajakio.test_client_id'))
            else:
                record.l10n_id_pajakio_hide_register =  bool(config_param.get_param('l10n_id_pajakio.email') and config_param.get_param('l10n_id_pajakio.password'))
                record.l10n_id_pajakio_hide_register_company = bool(config_param.get_param('l10n_id_pajakio.client_id'))

    def _compute_l10n_id_pajakio_linked(self):
        """ Compute whether the pajak.io service is linked or not """
        config_param = self.env['ir.config_parameter'].sudo()
        for record in self:
            record.l10n_id_pajakio_linked = bool(config_param.get_param('l10n_id_pajakio.active'))
