import contextlib

from odoo import _, api, fields, models, modules
from odoo.exceptions import RedirectWarning, UserError, ValidationError

from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
#from odoo.addons.l10n_dk_nemhandel.tools.demo_utils import handle_demo


class MojEracunRegistration(models.TransientModel):
    _name = 'mojeracun.registration'
    _description = "MojEracun Registration"

    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        default=lambda self: self.env.company,
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
    l10n_hr_mer_proxy_state = fields.Selection(related='company_id.l10n_hr_mer_proxy_state', readonly=False)
    mer_username = fields.Char("MojEracun username")
    mer_password = fields.Char("MojEracun password")
    mer_company_id = fields.Char("MojEracun CompanyId")
    mer_company_bu = fields.Char("MojEracun CompanyBu", default=None)
    mer_software_id = fields.Char("MojEracun SoftwareId")

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('company_id.account_edi_proxy_client_ids')
    def _compute_edi_user_id(self):
        for wizard in self:
            wizard.edi_user_id = wizard.company_id.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'mojeracun')[:1]

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

    def _action_open_mojeracun_form(self, reopen=True):
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
    def button_mojeracun_registration_activate(self):
        """
        Creates an MojEracun proxy user object and fills in user-provided credentials.
        The user is expected to apply for registration on the provider website.
        """
        self.ensure_one()

        if self.l10n_hr_mer_proxy_state != 'not_registered':
            raise UserError(_('Cannot register a user with a %s application', self.l10n_hr_mer_proxy_state))

        if not self.mer_username or not self.mer_password:
            raise ValidationError(_("Please enter MojEracun username and password."))
        if not self.mer_company_id or not self.mer_software_id:
            raise ValidationError(_("Please enter MojEracun company and software identifiers."))

        if not self.edi_user_id:
            edi_user = self.edi_user_id.sudo()._mer_register_proxy_user(
                self.company_id, 'mojeracun', self.edi_mode,
                self.mer_username, self.mer_password, self.mer_company_id, self.mer_company_bu, self.mer_software_id
            )
            self.edi_user_id = edi_user

            # if there is an error when activating the participant below,
            # the client side is rolled back and the edi user is deleted on the client side
            # but remains on the proxy side.
            # it is important to keep these two in sync, so commit before activating.
            if not modules.module.current_test:
                self.env.cr.commit()

        # Does nothing currently
        self.edi_user_id._check_user_on_alternative_service()

        self.company_id.l10n_hr_mer_proxy_state = 'receiver'
        return self._action_send_notification(
            title=_("Registered to receive documents."),
            message=_("You can now receive documents via MojEracun."),
        )

    #@handle_demo
    def button_mojeracun_receiver_registration(self):
        """
        The user is registered on the MojEracun network, i.e. can receive documents from other MojEracun participants.
        """
        self.ensure_one()
        try:
            #self.edi_user_id._eracun_register_as_receiver()
            self.edi_user_id._mer_register_proxy_user(
                self.company_id, 'mojeracun', self.edi_mode,
                self.mer_username, self.mer_password, self.mer_company_id, self.mer_company_bu, self.mer_software_id
            )
        except (UserError, AccountEdiProxyError) as e:
            self.button_deregister_mojeracun_participant()
            registration_form_action = self._action_open_mojeracun_form()
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

        if self.company_id.l10n_hr_mer_proxy_state == 'receiver':
            return self._action_send_notification(
                title=_("Registered to receive documents."),
                message=_("You can now receive documents via MojEracun."),
            )
        return self._action_open_mojeracun_form()

    #@handle_demo
    def button_update_mojeracun_user_data(self):
        """
        Action for the user to be able to update their contact details any time
        """
        self.ensure_one()

        if not self.mer_username or not self.mer_password:
            raise ValidationError(_("Please enter MojEracun username and password."))
        if not self.mer_company_id or not self.mer_software_id:
            raise ValidationError(_("Please enter MojEracun company and software identifiers."))
        # We don't need to send anything, the form is just there?..

    #@handle_demo
    def button_deregister_mojeracun_participant(self):
        """
        Deregister the edi user from eRacun network
        """
        self.ensure_one()

        if self.edi_user_id:
            self.edi_user_id._mer_deregister_participant()
        return True
