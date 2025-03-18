# Part of Odoo. See LICENSE file for full copyright and licensing details.
import contextlib
try:
    import phonenumbers
except ImportError:
    phonenumbers = None

from odoo import _, api, fields, models, modules
from odoo.exceptions import UserError, ValidationError

from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError


class PeppolRegistration(models.TransientModel):
    _name = 'peppol.registration'
    _description = "Peppol Registration"

    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    edi_mode = fields.Selection(
        string='EDI mode',
        selection=[('demo', 'Demo'), ('test', 'Test'), ('prod', 'Live')],
        compute='_compute_edi_mode',
    )
    edi_user_id = fields.Many2one(
        comodel_name='account_edi_proxy_client.user',
        string='EDI user',
        compute='_compute_edi_user_id',
    )
    account_peppol_proxy_state = fields.Selection(related='company_id.account_peppol_proxy_state')
    peppol_warnings = fields.Json(
        string="Peppol warnings",
        compute="_compute_peppol_warnings",
    )
    contact_email = fields.Char(
        related='company_id.account_peppol_contact_email',
        readonly=False,
        required=True,
    )
    phone_number = fields.Char(related='company_id.account_peppol_phone_number', readonly=False)
    peppol_eas = fields.Selection(related='company_id.peppol_eas', readonly=False, required=True)
    peppol_endpoint = fields.Char(related='company_id.peppol_endpoint', readonly=False, required=True)
    smp_registration = fields.Boolean(  # TODO switch to computed non-stored in master
        string='Register as a receiver',
        help="If not check, you will only be able to send invoices but not receive them.",
        compute='_compute_smp_registration',
        store=True,
        readonly=False,
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

    @api.depends('peppol_eas', 'peppol_endpoint', 'smp_registration')
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
            if not wizard.smp_registration:
                peppol_warnings['company_on_another_smp'] = {
                    'message': _("Your company is already registered on another Access Point for receiving invoices. "
                                 "We will register you as a sender only.")
                }
            wizard.peppol_warnings = peppol_warnings or False

    @api.depends('peppol_eas', 'peppol_endpoint')
    def _compute_smp_registration(self):
        for wizard in self:
            wizard.smp_registration = False
            if wizard.peppol_eas and wizard.peppol_endpoint:
                try:
                    edi_identification = f'{wizard.peppol_eas}:{wizard.peppol_endpoint}'
                    wizard.edi_user_id._check_company_on_peppol(wizard.company_id, edi_identification)
                    wizard.smp_registration = True
                except UserError:
                    pass

    @api.depends('company_id', 'edi_user_id')
    def _compute_edi_mode(self):
        for wizard in self:
            wizard.edi_mode = wizard.company_id._get_peppol_edi_mode()

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
            'context': {
                'dialog_size': 'medium',
                **self.env.context,
            },
        }

        if reopen:
            action_dict.update({
                'res_id': self.id,
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
                edi_user._peppol_get_participant_status()
            except (UserError, AccountEdiProxyError):
                edi_user._peppol_deregister_participant()
                raise

        # success or rejected
        notifications = {
            'sender': {
                'message': _('You can now send electronic invoices via Peppol.'),
            },
            'smp_registration': {
                'message': _('Your Peppol registration will be activated soon. You can already send invoices.'),
            },
            'receiver': {
                'message': _('You can now send and receive electronic invoices via Peppol'),
            },
            'rejected': {
                'title': _('Registration rejected.'),
                'message': _('Your registration has been rejected. Please contact the support for further assistance.'),
            },
        }
        state = self.company_id.account_peppol_proxy_state
        return self._action_send_notification(
            title=None,
            message=notifications[state]['message'],
        )
