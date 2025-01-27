# Part of Odoo. See LICENSE file for full copyright and licensing details.
import contextlib
try:
    import phonenumbers
except ImportError:
    phonenumbers = None

from odoo import _, api, fields, models, modules
from odoo.exceptions import UserError, ValidationError

from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.addons.account_peppol.tools.demo_utils import handle_demo


class PeppolRegistration(models.TransientModel):
    _name = 'peppol.registration'
    _description = "Peppol Registration"

    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    contact_email = fields.Char(
        related='company_id.account_peppol_contact_email',
        readonly=False,
        required=True,
    )
    edi_mode = fields.Selection(
        string='EDI mode',
        selection=[('demo', 'Demo'), ('test', 'Test'), ('prod', 'Live')],
        compute='_compute_edi_mode',
        inverse='_inverse_edi_mode',
        readonly=False,
    )
    edi_user_id = fields.Many2one(
        comodel_name='account_edi_proxy_client.user',
        string='EDI user',
        compute='_compute_edi_user_id',
    )
    account_peppol_migration_key = fields.Char(related='company_id.account_peppol_migration_key', readonly=False)  # TODO remove in master
    edi_mode_constraint = fields.Selection(
        selection=[('demo', 'Demo'), ('test', 'Test'), ('prod', 'Live')],
        compute='_compute_edi_mode_constraint',
        help="Using the config params, this field specifies which edi modes may be selected from the UI"
    )
    phone_number = fields.Char(related='company_id.account_peppol_phone_number', readonly=False)
    account_peppol_proxy_state = fields.Selection(related='company_id.account_peppol_proxy_state', readonly=False)
    verification_code = fields.Char(related='edi_user_id.peppol_verification_code', readonly=False)  # TODO remove in master
    peppol_eas = fields.Selection(related='company_id.peppol_eas', readonly=False, required=True)
    peppol_endpoint = fields.Char(related='company_id.peppol_endpoint', readonly=False, required=True)
    peppol_warnings = fields.Json(
        string="Peppol warnings",
        compute="_compute_peppol_warnings",
    )
    smp_registration = fields.Boolean(
        string='Register as a receiver',
        help="If not check, you will only be able to send invoices but not receive them.",
        default=True,
    )

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('peppol_endpoint')
    def _onchange_peppol_endpoint(self):
        for wizard in self:
            if wizard.peppol_endpoint:
                wizard.peppol_endpoint = ''.join(char for char in wizard.peppol_endpoint if char.isalnum())

    @api.onchange('phone_number')
    def _onchange_phone_number(self):
        for wizard in self:
            if wizard.phone_number:
                wizard.company_id._sanitize_peppol_phone_number(wizard.phone_number)
                with contextlib.suppress(phonenumbers.NumberParseException):
                    parsed_phone_number = phonenumbers.parse(
                        wizard.phone_number,
                        region=self.company_id.country_code,
                    )
                    wizard.phone_number = phonenumbers.format_number(
                        parsed_phone_number,
                        phonenumbers.PhoneNumberFormat.E164,
                    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('company_id.account_edi_proxy_client_ids')
    def _compute_edi_user_id(self):
        for wizard in self:
            wizard.edi_user_id = wizard.company_id.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'peppol')[:1]

    @api.depends('peppol_eas', 'peppol_endpoint')
    def _compute_peppol_warnings(self):
        for wizard in self:
            peppol_warnings = {}
            if (
                wizard.peppol_eas
                and wizard.peppol_endpoint
                and not wizard.company_id._check_peppol_endpoint_number(warning=True)
            ):
                peppol_warnings['company_peppol_endpoint_warning'] = {
                    'message': _("The endpoint number might not be correct. "
                                "Please check if you entered the right identification number."),
                }
            if wizard.company_id.country_code == 'BE' and wizard.peppol_eas not in (False, '0208'):
                peppol_warnings['company_peppol_eas_warning'] = {
                    'message': _("The recommended EAS code for Belgium is 0208. "
                                "The Endpoint should be the Company Registry number."),
                }
            wizard.peppol_warnings = peppol_warnings or False

    @api.depends('edi_user_id')
    def _compute_edi_mode_constraint(self):
        mode_constraint = self.env['ir.config_parameter'].sudo().get_param('account_peppol.mode_constraint')
        trial_param = self.env['ir.config_parameter'].sudo().get_param('saas_trial.confirm_token')
        self.edi_mode_constraint = trial_param and 'demo' or mode_constraint or 'prod'

    @api.depends('edi_user_id')
    def _compute_edi_mode(self):
        edi_mode = self.env['ir.config_parameter'].sudo().get_param('account_peppol.edi.mode')
        for wizard in self:
            if wizard.edi_user_id:
                wizard.edi_mode = wizard.edi_user_id.edi_mode
            else:
                wizard.edi_mode = edi_mode or 'prod'

    def _inverse_edi_mode(self):
        for wizard in self:
            if not wizard.edi_user_id and wizard.edi_mode:
                self.env['ir.config_parameter'].sudo().set_param('account_peppol.edi.mode', wizard.edi_mode)
                return

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def _ensure_mandatory_fields(self):
        if not self.contact_email or not self.phone_number:
            raise ValidationError(_("Contact email and phone number are required."))

    def _action_open_peppol_form(self, reopen=True):
        action_dict = {
            'name': _("Activate Electronic Invoicing (via Peppol)"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'peppol.registration',
            'target': 'new',
            'context': self.env.context,
        }

        if reopen:
            action_dict.update({
                'res_id': self.id,
                'context': {**self.env.context, 'disable_sms_verification': True},
            })
        return action_dict

    def _action_send_notification(self, title, message):
        move_ids = self.env.context.get('active_ids')
        if move_ids and self.env.context.get('active_model') == 'account.move':
            next_action = self.env['account.move'].browse(move_ids).action_send_and_print()
            next_action['views'] = [(False, 'form')]
        else:
            next_action = {'type': 'ir.actions.act_window_close'}

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'type': 'success',
                'message': message,
                'next': next_action,
            }
        }

    @handle_demo
    def button_peppol_sender_registration(self):
        """ TODO remove in master
        The first step of the Peppol onboarding.
        - Creates an EDI proxy user on the iap side, then the client side
        - Calls /activate_participant to mark the EDI user as peppol user
        - Allows the user to become a sender but not a receiver on the Peppol network.
        Basically, a Sender does not exist on the peppol network. They use our
        Access Point to send invoices to Peppol participants without having to register
        themselves.
        """
        self.button_register_peppol_participant()

    @handle_demo
    def button_peppol_smp_registration(self):
        """ TODO remove in master
        The second (optional) step in Peppol registration.
        The user can choose to become a Receiver and officially register on the Peppol
        network, i.e. receive documents from other Peppol participants.
        """
        self.button_register_peppol_participant()

    @handle_demo
    def button_update_peppol_user_data(self):
        """
        Action for the user to be able to update their contact details any time
        Calls /update_user on the iap server
        """
        self.ensure_one()
        self._ensure_mandatory_fields()

        edi_identification = f'{self.peppol_eas}:{self.peppol_endpoint}'
        if self.smp_registration:
            self.edi_user_id._check_company_on_peppol(self.company_id, edi_identification)

        params = {
            'update_data': {
                'edi_identification': edi_identification,
                'peppol_phone_number': self.phone_number,
                'peppol_contact_email': self.contact_email,
            }
        }

        self.edi_user_id._call_peppol_proxy(
            endpoint='/api/peppol/1/update_user',
            params=params,
        )
        return True

    def button_send_peppol_verification_code(self):
        """ TODO remove in master
        Request user verification via SMS
        Calls the /send_verification_code to send the 6-digit verification code
        """
        pass

    @handle_demo
    def button_check_peppol_verification_code(self):
        """ TODO remove in master
        Calls /verify_phone_number to compare user's input and the
        code generated on the IAP server
        """
        pass

    @handle_demo
    def button_register_peppol_participant(self):
        self.ensure_one()
        self._ensure_mandatory_fields()

        if self.account_peppol_proxy_state in ('smp_registration', 'receiver', 'rejected'):
            raise UserError(
                _('Cannot register a user with a %s application', self.account_peppol_proxy_state))

        edi_user = self.edi_user_id or self.env['account_edi_proxy_client.user']._register_proxy_user(self.company_id, 'peppol', self.edi_mode)

        # if there is an error when activating the participant below,
        # the client side is rolled back and the edi user is deleted on the client side
        # but remains on the proxy side.
        # it is important to keep these two in sync, so commit before activating.
        if not modules.module.current_test:
            self.env.cr.commit()

        edi_user._peppol_register_sender()

        if self.smp_registration:
            try:
                edi_user._peppol_register_sender_as_receiver()
            except (UserError, AccountEdiProxyError) as e:
                self.button_deregister_peppol_participant()
                raise

        # success
        notifications = {
            'sender': {
                'title': _('Registered as a sender.'),
                'message': _('You can now send electronic invoices via Peppol.'),
            },
            'smp_registration': {  # TODO remove in master
                'title': _('Registered to receive documents via Peppol.'),
                'message': _('Your registration on Peppol network should be activated within a day. The updated status will be visible in Settings.'),
            },
            'receiver': {
                'title': _('Registered as a receiver.'),
                'message': _('You can now send and receive electronic invoices via Peppol'),
            },
        }
        state = self.company_id.account_peppol_proxy_state
        return self._action_send_notification(
            title=notifications[state]['title'],
            message=notifications[state]['message'],
        )

    @handle_demo
    def button_deregister_peppol_participant(self):
        """
        Deregister the edi user from Peppol network
        """
        self.ensure_one()

        if self.edi_user_id:
            self.edi_user_id._peppol_deregister_participant()
        return True
