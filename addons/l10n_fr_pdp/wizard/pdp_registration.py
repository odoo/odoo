import contextlib
try:
    import phonenumbers
except ImportError:
    phonenumbers = None

from odoo import _, api, fields, models, modules
from odoo.exceptions import UserError, ValidationError


class PdpRegistration(models.TransientModel):
    _name = 'pdp.registration'
    _description = "PDP Registration"

    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    contact_email = fields.Char(
        related='company_id.pdp_contact_email',
        readonly=False,
        required=True,
    )
    phone_number = fields.Char(related='company_id.pdp_phone_number', readonly=False)
    pdp_identifier = fields.Char(related='company_id.pdp_identifier', readonly=False, required=True)
    edi_mode = fields.Selection(
        string='EDI mode',
        selection=[('demo', 'Demo'), ('test', 'Test'), ('prod', 'Live')],
        compute='_compute_edi_mode',
        readonly=False,
    )
    edi_user_id = fields.Many2one(
        comodel_name='account_edi_proxy_client.user',
        string='EDI user',
        compute='_compute_edi_user_id',
    )
    l10n_fr_pdp_proxy_state = fields.Selection(related='company_id.l10n_fr_pdp_proxy_state', readonly=False)
    warnings = fields.Json(
        string="Warnings",
        compute="_compute_warnings",
    )

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('pdp_identifier')
    def _onchange_pdp_identifier(self):
        for wizard in self:
            if wizard.pdp_identifier:
                wizard.pdp_identifier = ''.join(char for char in wizard.pdp_identifier if char == '_' or char.isalnum())

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
            wizard.edi_user_id = wizard.company_id.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'pdp')[:1]

    @api.depends('edi_user_id')
    def _compute_edi_mode(self):
        for wizard in self:
            wizard.edi_mode = wizard.company_id._get_pdp_edi_mode()

    @api.depends('pdp_identifier')
    def _compute_warnings(self):
        for wizard in self:
            warnings = {}
            if (
                wizard.pdp_identifier
                and not wizard.company_id._check_pdp_identifier(wizard.pdp_identifier, warning=True)
            ):
                warnings['company_pdp_identifier_warning'] = {
                    'level': 'warning',
                    'message': _("The endpoint number might not be correct. "
                                "Please check if you entered the right identification number."),
                }
            # TODO: check annuaire whether it is already registered
            wizard.warnings = warnings or False

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _ensure_mandatory_fields(self):
        if not self.contact_email or not self.phone_number:
            raise ValidationError(_("Contact email and phone number are required."))

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

    def _action_open_pdp_form(self, reopen=True):
        return self._get_records_action(
            name=_("Send via PDP"),
            target='new',
        )

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def button_register_pdp_participant(self):
        self.ensure_one()

        self._ensure_mandatory_fields()

        if self.l10n_fr_pdp_proxy_state in ('pending', 'receiver'):
            pdp_state_translated = dict(self._fields['l10n_fr_pdp_proxy_state'].selection)[self.l10n_fr_pdp_proxy_state]
            raise UserError(
                _('Cannot register a user with a %s application', pdp_state_translated))

        edi_user = self.edi_user_id or self.env['account_edi_proxy_client.user']._register_proxy_user(self.company_id, 'pdp', self.edi_mode)

        # if there is an error when activating the participant below,
        # the client side is rolled back and the edi user is deleted on the client side
        # but remains on the proxy side.
        # it is important to keep these two in sync, so commit before activating.
        if not modules.module.current_test:
            self.env.cr.commit()

        if self.l10n_fr_pdp_proxy_state not in ('pending', 'receiver'):
            edi_user._pdp_register_receiver()
            self.invalidate_recordset()  # registering may i.e. have changed self.l10n_fr_pdp_proxy_state

        notifications = {
            False: _('Something went wrong.'),
            'pending': _('Your registration will be activated soon.'),
            'receiver': _('You can now send and receive electronic invoices.'),
            'rejected': _('Your registration has been rejected.'),
        }
        return self._action_send_notification(
            title="PDP Status",
            message=notifications[self.l10n_fr_pdp_proxy_state],
        )

    def button_deregister_pdp_participant(self):
        """
        Deregister the edi user from PDP network
        """
        self.ensure_one()

        if self.edi_user_id:
            self.edi_user_id._pdp_deregister_participant()
