import contextlib

from odoo import _, api, fields, models, modules
from odoo.exceptions import RedirectWarning, UserError, ValidationError

from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
#from odoo.addons.l10n_dk_nemhandel.tools.demo_utils import handle_demo


class EracunRegistration(models.TransientModel):
    _name = 'eracun.registration'
    _description = "eRacun Registration"

    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    contact_email = fields.Char(
        related='company_id.eracun_contact_email',
        readonly=False,
        required=True,
    )
    edi_mode = fields.Selection(
        string='EDI mode',
        selection=[('test', 'Test'), ('prod', 'Live')], # ('demo', 'Demo') is currently not supported
        compute='_compute_edi_mode',
        inverse='_inverse_edi_mode',
        readonly=False,
    )
    edi_user_id = fields.Many2one(
        comodel_name='account_edi_proxy_client.user',
        string='EDI user',
        compute='_compute_edi_user_id',
    )
    l10n_hr_eracun_proxy_state = fields.Selection(related='company_id.l10n_hr_eracun_proxy_state', readonly=False)
    identifier_type = fields.Selection(related='company_id.eracun_identifier_type', readonly=False, required=True)
    identifier_value = fields.Char(related='company_id.eracun_identifier_value', readonly=False, required=True)

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('identifier_value')
    def _onchange_identifier_value(self):
        for wizard in self:
            if wizard.identifier_value:
                wizard.identifier_value = ''.join(char for char in wizard.identifier_value if char.isalnum())

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('company_id.account_edi_proxy_client_ids')
    def _compute_edi_user_id(self):
        for wizard in self:
            wizard.edi_user_id = wizard.company_id.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'eracun')[:1]

    @api.depends('edi_user_id')
    def _compute_edi_mode(self):
        edi_mode = self.env['ir.config_parameter'].sudo().get_param('l10n_hr_eracun.edi.mode')
        for wizard in self:
            if wizard.edi_user_id:
                wizard.edi_mode = wizard.edi_user_id.edi_mode
            else:
                wizard.edi_mode = edi_mode or 'prod'

    def _inverse_edi_mode(self):
        for wizard in self:
            if not wizard.edi_user_id and wizard.edi_mode:
                self.env['ir.config_parameter'].sudo().set_param('l10n_hr_eracun.edi.mode', wizard.edi_mode)

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def _action_open_eracun_form(self, reopen=True):
        if reopen:
            return self._get_records_action(
                name=_("Send via eRacun"),
                res_id=self.id,
                target='new',
                context={**self.env.context, 'disable_sms_verification': True},
            )

        return self._get_records_action(
            name=_("Send via eRacun"),
            target='new',
            context={**self.env.context, 'disable_sms_verification': True}, # I think this is required if we are not using SMS verification for HR
        )

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

    #@handle_demo
    def button_eracun_registration_activate(self):
        """
        - Creates an EDI proxy user on the iap side, then the client side
        - Calls /activate_participant to mark the EDI user as eRacun user
        """
        self.ensure_one()

        if self.l10n_hr_eracun_proxy_state != 'not_registered':
            raise UserError(_('Cannot register a user with a %s application', self.l10n_hr_eracun_proxy_state))

        if not self.contact_email:
            raise ValidationError(_("Please enter a primary contact email to verify your application."))
        if not self.env.company.vat:
            raise RedirectWarning(
                _("Please fill in your company's VAT"),
                self.env.ref('base.action_res_company_form').id,
                _('Company settings')
            )

        if not self.edi_user_id:
            edi_user = self.edi_user_id.sudo()._register_proxy_user(self.company_id, 'eracun', self.edi_mode)
            self.edi_user_id = edi_user

            # if there is an error when activating the participant below,
            # the client side is rolled back and the edi user is deleted on the client side
            # but remains on the proxy side.
            # it is important to keep these two in sync, so commit before activating.
            if not modules.module.current_test:
                self.env.cr.commit()

        self.edi_user_id._check_user_on_alternative_service()

        self.company_id.l10n_hr_eracun_proxy_state = 'receiver'
        return self._action_send_notification(
            title=_("Registered to receive documents."),
            message=_("You can now receive documents via eRacun."),
        )

    #@handle_demo
    def button_eracun_receiver_registration(self):
        """
        The user is registered on the eRacun network, i.e. can receive documents from other eRacun participants.
        """
        self.ensure_one()
        try:
            self.edi_user_id._eracun_register_as_receiver()
        except (UserError, AccountEdiProxyError) as e:
            self.button_deregister_eracun_participant()
            registration_form_action = self._action_open_eracun_form()
            registration_form_action['views'] = [(False, 'form')]
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': e,
                    'next': registration_form_action,
                }
            }

        if self.company_id.l10n_hr_eracun_proxy_state == 'receiver':
            return self._action_send_notification(
                title=_("Registered to receive documents."),
                message=_("You can now receive documents via eRacun."),
            )
        return self._action_open_eracun_form()

    #@handle_demo
    def button_update_eracun_user_data(self):
        """
        Action for the user to be able to update their contact details any time
        Calls /update_user on the iap server
        """
        self.ensure_one()

        if not self.contact_email:
            raise ValidationError(_("Contact email is required."))

        params = {
            'update_data': {
                'eracun_contact_email': self.contact_email,
            }
        }

        self.edi_user_id._call_eracun_proxy(
            endpoint='/api/eracun/1/update_user',
            params=params,
        )

    #@handle_demo
    def button_deregister_eracun_participant(self):
        """
        Deregister the edi user from eRacun network
        """
        self.ensure_one()

        if self.edi_user_id:
            self.edi_user_id._eracun_deregister_participant()
        self.verification_code = False
        return True
