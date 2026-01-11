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

    # 'company_id' is the current active company, always set.
    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        default=lambda self: self.env.company,
    )

    # 'parent_company_id' is the potential parent company of the current branch or the branch itself
    # if no fallback on the parent branch is possible.
    parent_company_id = fields.Many2one(
        comodel_name='res.company',
        compute='_compute_parent_company_id'
    )
    parent_company_name = fields.Char(related='parent_company_id.name')

    # 'selected_company_id' could be 'company_id' if 'use_parent_connection_selection' is 'use_self'
    # or 'parent_company_id' if 'use_parent_connection_selection' is 'use_parent'.
    selected_company_id = fields.Many2one(
        comodel_name='res.company',
        compute='_compute_selected_company_id',
    )

    # Choice between the current company or the parent one.
    display_use_parent_connection_selection = fields.Boolean(
        compute='_compute_display_use_parent_connection_selection',
    )
    use_parent_connection_selection = fields.Selection(
        selection=[
            ('use_parent', "Send from parent company"),
            ('use_self', "Register this company on peppol"),
        ],
        compute='_compute_use_parent_connection_selection',
        store=True,
        readonly=False,
    )
    use_parent_connection = fields.Boolean(compute='_compute_use_parent_connection')

    # TODO: remove in master
    is_branch_company = fields.Boolean(store=False)
    active_parent_company = fields.Many2one(string="Active Parent Company", related='parent_company_id')
    active_parent_company_name = fields.Char(string="Active Parent Company Name", related='parent_company_name')
    can_use_parent_connection = fields.Boolean(string="Can Use Parent Connection", related='display_use_parent_connection_selection')
    # TODO END: remove in master

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
    account_peppol_proxy_state = fields.Selection(related='selected_company_id.account_peppol_proxy_state')
    peppol_warnings = fields.Json(
        string="Peppol warnings",
        compute="_compute_peppol_warnings",
    )
    contact_email = fields.Char(
        related='selected_company_id.account_peppol_contact_email',
        readonly=False,
        required=True,
    )
    phone_number = fields.Char(related='selected_company_id.account_peppol_phone_number', readonly=False)
    peppol_eas = fields.Selection(related='selected_company_id.peppol_eas', readonly=False, required=True)
    peppol_endpoint = fields.Char(related='selected_company_id.peppol_endpoint', readonly=False, required=True)
    smp_registration = fields.Boolean(  # you're registering to SMP when you register as a sender+receiver
        string='Register as a receiver',
        compute='_compute_smp_registration_external_provider'
    )
    peppol_external_provider = fields.Char(compute='_compute_smp_registration_external_provider')

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
        self.env['res.company']._check_phonenumbers_import()
        for wizard in self:
            if wizard.phone_number:
                # The `phone_number` we set is not necessarily valid (may fail `_sanitize_peppol_phone_number`)
                with contextlib.suppress(phonenumbers.NumberParseException):
                    parsed_phone_number = phonenumbers.parse(
                        wizard.phone_number,
                        region=wizard.selected_company_id.country_code,
                    )
                    wizard.phone_number = phonenumbers.format_number(
                        parsed_phone_number,
                        phonenumbers.PhoneNumberFormat.E164,
                    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('company_id')
    def _compute_parent_company_id(self):
        for wizard in self:
            wizard.parent_company_id = wizard.company_id.peppol_parent_company_id or wizard.company_id

    @api.depends('parent_company_id')
    def _compute_display_use_parent_connection_selection(self):
        for wizard in self:
            wizard.display_use_parent_connection_selection = wizard.company_id != wizard.parent_company_id

    @api.depends('display_use_parent_connection_selection')
    def _compute_use_parent_connection_selection(self):
        for wizard in self:
            if wizard.display_use_parent_connection_selection:
                wizard.use_parent_connection_selection = 'use_parent' if wizard.parent_company_id.peppol_can_send else 'use_self'
            else:
                wizard.use_parent_connection_selection = 'use_self'

    @api.depends('use_parent_connection_selection')
    def _compute_use_parent_connection(self):
        for wizard in self:
            wizard.use_parent_connection = (
                wizard.display_use_parent_connection_selection
                and wizard.use_parent_connection_selection == 'use_parent'
            )

    @api.depends('use_parent_connection')
    def _compute_selected_company_id(self):
        for wizard in self:
            if wizard.use_parent_connection:
                wizard.selected_company_id = wizard.parent_company_id
            else:
                wizard.selected_company_id = wizard.company_id

    @api.depends('selected_company_id.account_edi_proxy_client_ids')
    def _compute_edi_user_id(self):
        for wizard in self:
            wizard.edi_user_id = wizard.company_id.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'peppol')[:1]

    @api.depends('selected_company_id', 'peppol_eas', 'peppol_endpoint', 'smp_registration', 'peppol_external_provider', 'use_parent_connection')
    def _compute_peppol_warnings(self):
        for wizard in self:
            peppol_warnings = {}
            if all((
                wizard.peppol_eas,
                wizard.peppol_endpoint,
                not wizard.selected_company_id._check_peppol_endpoint_number(warning=True),
            )):
                peppol_warnings['company_peppol_endpoint_warning'] = {
                    'level': 'warning',
                    'message': _("The endpoint number might not be correct. "
                                 "Please check if you entered the right identification number."),
                }
            if all((
                not wizard.use_parent_connection,
                wizard.peppol_eas,
                wizard.peppol_endpoint,
                not wizard.smp_registration,
            )):
                peppol_warnings['company_already_on_smp'] = {
                    'level': 'info',
                    'message': _("Your company is already registered on an Access Point (%s) for receiving invoices. "
                                 "We will register you on Odoo as a sender only.", wizard.peppol_external_provider)
                }
            if wizard.peppol_eas == '9925':
                peppol_warnings['be_9925_warning'] = {
                    'level': 'warning',
                    'message': _("You are about to register with your VAT number. Make sure you register with your "
                                "Company Registry (BCE/KBO) first to be compliant with the new regulation."),
                }
            wizard.peppol_warnings = peppol_warnings or False

    @api.depends('selected_company_id', 'edi_user_id', 'peppol_eas')
    def _compute_edi_mode(self):
        for wizard in self:
            wizard.edi_mode = wizard.company_id._get_peppol_edi_mode(temporary_eas=wizard.peppol_eas)

    @api.depends('selected_company_id', 'peppol_eas', 'peppol_endpoint')
    def _compute_smp_registration_external_provider(self):
        for wizard in self:
            is_company_on_peppol = True
            external_provider = None
            if wizard.peppol_eas and wizard.peppol_endpoint:
                edi_identification = f'{wizard.peppol_eas}:{wizard.peppol_endpoint}'
                peppol_info = wizard.company_id._get_company_info_on_peppol(edi_identification)
                is_company_on_peppol = peppol_info['is_on_peppol']
                external_provider = peppol_info['external_provider']
            wizard.smp_registration = not is_company_on_peppol  # Register on smp if not on Peppol
            wizard.peppol_external_provider = external_provider

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def _branch_with_same_address(self):
        self.ensure_one()
        return (
            not self.use_parent_connection
            and self.company_id != self.parent_company_id
            and self.peppol_eas == self.parent_company_id.peppol_eas
            and self.peppol_endpoint == self.parent_company_id.peppol_endpoint
        )

    def _ensure_mandatory_fields(self):
        if self.use_parent_connection:
            return
        if not self.contact_email or not self.phone_number:
            raise ValidationError(_("Contact email and phone number are required."))
        if not self.peppol_eas or not self.peppol_endpoint:
            raise ValidationError(_("Peppol Address should be provided."))
        if self._branch_with_same_address():
            raise ValidationError(_("Peppol ID should be different from main company."))

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

        if self.use_parent_connection:
            self.company_id.write({
                'peppol_eas': self.peppol_eas,
                'peppol_endpoint': self.peppol_endpoint,
                'account_peppol_contact_email': self.contact_email,
                'account_peppol_phone_number': self.phone_number,
            })

        edi_user = self.edi_user_id or self.env['account_edi_proxy_client.user']._register_proxy_user(self.company_id, 'peppol', self.edi_mode)

        # if there is an error when activating the participant below,
        # the client side is rolled back and the edi user is deleted on the client side
        # but remains on the proxy side.
        # it is important to keep these two in sync, so commit before activating.
        if not modules.module.current_test:
            self.env.cr.commit()

        edi_user._peppol_register_sender(peppol_external_provider=self.peppol_external_provider)

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

        if state == 'sender':
            # if user asked to register as a receiver, state would've been 'smp_registration'
            # so this is the final registration state for sender-only registration
            self.company_id._account_peppol_send_welcome_email()

        return self._action_send_notification(
            title=None,
            message=notifications[state]['message'],
        )
