# Part of Odoo. See LICENSE file for full copyright and licensing details.
import contextlib
try:
    import phonenumbers
except ImportError:
    phonenumbers = None

from odoo import _, api, fields, models, modules
from odoo.exceptions import UserError

from odoo.addons.account.models.res_partner_identification import ODOO_IDENTIFIER_VALUES
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError

PEPPOL_CODES_SELECTION = [
    (identifier_vals['schemeid'], identifier_vals.get('odoo-name') or identifier_vals['scheme-name'])
    for identifier_vals
    in ODOO_IDENTIFIER_VALUES
    if identifier_vals.get('state') == 'active' and identifier_vals.get('peppol-registrable', False)
]
# This list depends on Country specific rules defined by Peppol Authorities.
# https://openpeppol.atlassian.net/wiki/spaces/AF/pages/2889318401/Peppol+Authority+Specific+Requirements
MANDATORY_EAS_MAPPING = {
    'BE': ['BE:EN'],
}


class PeppolRegistrationWizard(models.TransientModel):
    _name = 'peppol.registration.wizard'
    _description = "Peppol Registration Wizard"

    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    country_id = fields.Many2one(
        comodel_name='res.country',
        related='company_id.country_id',
        readonly=False,
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
    phone_number = fields.Char(
        related='company_id.account_peppol_phone_number',
        readonly=False,
        required=True,
    )
    force_mandatory_eas = fields.Boolean(compute='_compute_force_mandatory_eas')
    peppol_eas = fields.Selection(
        selection=PEPPOL_CODES_SELECTION,
        compute='_compute_peppol_eas',
        store=True,
        readonly=False,
        required=True,
    )
    available_peppol_eas = fields.Json(compute='_compute_available_peppol_eas')
    peppol_endpoint = fields.Char(compute='_compute_peppol_endpoint', store=True, readonly=False, required=True)
    smp_registration = fields.Boolean(  # you're registering to SMP when you register as a sender+receiver
        string='Register as a receiver',
        compute='_compute_smp_registration_external_provider'
    )
    peppol_external_provider = fields.Char(compute='_compute_smp_registration_external_provider')

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('phone_number')
    def _onchange_phone_number(self):
        self.env['res.company']._check_phonenumbers_import()
        for wizard in self:
            if wizard.phone_number:
                # The `phone_number` we set is not necessarily valid (may fail `_sanitize_peppol_phone_number`)
                with contextlib.suppress(phonenumbers.NumberParseException):
                    parsed_phone_number = phonenumbers.parse(
                        wizard.phone_number,
                        region=wizard.company_id.country_code,
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

    @api.depends('peppol_eas', 'peppol_endpoint', 'smp_registration', 'peppol_external_provider')
    def _compute_peppol_warnings(self):
        for wizard in self:
            peppol_warnings = {}
            valid_endpoint, _error_message = self.env['res.partner.identification']._apply_validation_rules(wizard.peppol_eas, wizard.peppol_endpoint)
            if (
                wizard.peppol_eas
                and wizard.peppol_endpoint
                and not valid_endpoint
            ):
                peppol_warnings['company_peppol_endpoint_warning'] = {
                    'message': _("The endpoint number might not be correct. "
                                "Please check if you entered the right identification number."),
                }
            if not wizard.smp_registration:
                peppol_warnings['company_already_on_smp'] = {
                    'message': _("Your company is already registered on an Access Point (%s) for receiving invoices. "
                                 "We will register you on Odoo as a sender only.", wizard.peppol_external_provider)
                }
            wizard.peppol_warnings = peppol_warnings or False

    @api.depends('company_id', 'edi_user_id')
    def _compute_edi_mode(self):
        for wizard in self:
            wizard.edi_mode = wizard.company_id._get_peppol_edi_mode()

    @api.depends('country_id')
    def _compute_force_mandatory_eas(self):
        for wizard in self:
            wizard.force_mandatory_eas = wizard.country_id.code in MANDATORY_EAS_MAPPING

    @api.depends('country_id', 'force_mandatory_eas')
    def _compute_peppol_eas(self):
        for wizard in self:
            if wizard.force_mandatory_eas:
                wizard.peppol_eas = MANDATORY_EAS_MAPPING[wizard.country_id.code][0]
            else:
                wizard.peppol_eas = next(iter(self.env['res.partner.identification']._get_peppol_codes_by_country()))[0]

    @api.depends('country_id')
    def _compute_available_peppol_eas(self):
        for wizard in self:
            wizard.available_peppol_eas = []  # FIXME continue

    @api.depends('peppol_eas')
    def _compute_peppol_endpoint(self):
        for wizard in self:
            wizard.peppol_endpoint = wizard.company_id.partner_id.identifier_ids.filtered(lambda i: i.code == wizard.peppol_eas).identifier

    @api.depends('peppol_eas', 'peppol_endpoint')
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

    def _action_open_peppol_form(self, reopen=True):
        action_dict = {
            'name': _("Activate Electronic Invoicing (via Peppol)"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'peppol.registration.wizard',
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

    def button_register_peppol_participant(self):
        self.ensure_one()

        if self.account_peppol_proxy_state != 'not_registered':
            raise UserError(self.env._('Cannot re-register.', self.account_peppol_proxy_state))

        edi_user = self.edi_user_id or self.env['account_edi_proxy_client.user']._register_proxy_user(self.company_id, 'peppol', self.edi_mode)

        # if there is an error when activating the participant below,
        # the client side is rolled back, and the edi user is deleted on the client side
        # but remains on the proxy side.
        # it is important to keep these two in sync, so commit before activating.
        if not modules.module.current_test:
            self.env.cr.commit()

        try:
            self.env['account_edi_proxy_client.user']._peppol_register(smp_registration=self.smp_registration)
            state = edi_user._peppol_get_participant_status()
            self.company_id.partner_id._create_or_update_identification(self.peppol_eas, self.peppol_endpoint, is_on_odoo_peppol=True)
        except (UserError, AccountEdiProxyError):
            edi_user._peppol_deregister_participant()
            raise

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

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': notifications[state]['message'],
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
