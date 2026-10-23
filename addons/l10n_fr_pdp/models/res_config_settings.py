from types import MappingProxyType

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.l10n_fr_pdp.models.res_company import STUDIO_LEGAL_FORM, STUDIO_RCS_CITY, STUDIO_SHARE_CAPITAL

PEPPOL_PROXY_STATE_17_TO_18 = MappingProxyType({
    'not_registered': 'not_registered',
    'not_verified': 'in_verification',
    'sent_verification': 'in_verification',
    'pending': 'smp_registration',
    'active': 'receiver',
    'sender': 'sender',
    'rejected': 'rejected',
})


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # DEPRECATED - was for the pre-prod phase
    l10n_fr_pdp_pilot_phase = fields.Boolean(
        compute='_compute_l10n_fr_pdp_pilot_phase',
        inverse='_inverse_l10n_fr_pdp_pilot_phase',
        string="Pilot Phase",
        help="Participate in the Pilot Phase of the French E-Invoicing. This way you are able to test it before it becomes mandatory.",
    )
    l10n_fr_pdp_send_to_ppf = fields.Boolean(
        related='company_id.l10n_fr_pdp_send_to_ppf', readonly=False,
        string="Send to PPF",
        help="Activate Flux 1 regulatory data, Flux 6 mandatory statuses and Flux 10 e-reporting generation for this company.",
    )
    l10n_fr_pdp_annuaire_start_date = fields.Date(
        related='company_id.l10n_fr_pdp_annuaire_start_date',
        string="Annuaire Start Date",
        help="The date on which the company is registered on the annuaire for the French e-invoicing.",
    )
    l10n_fr_pdp_registered = fields.Boolean(
        related='company_id.l10n_fr_pdp_registered',
        string="Approved Platform Registered",
    )
    l10n_fr_pdp_periodicity = fields.Selection(
        string="Flow 10 Report Periodicity",
        related='company_id.l10n_fr_pdp_periodicity', readonly=False,
        required=True,
        help="""Legal reporting period for transaction and payments flows according to the TVA regime table.
        Real Monthly Normal Regime : transactions reported by decade, payments reported monthly
        Real Normal Quarterly Regime : transactions reported monthly, payments reported monthly
        Simplified VAT Regime (Monthly) : transactions reported monthly, payments reported monthly
        Franchised VAT Regime (Bimonthly) : transactions reported bimonthly, payments reported bimonthly
        """,
    )
    l10n_fr_pdp_legal_form = fields.Char(
        string='Legal Form',
        compute='_compute_l10n_fr_pdp_legal_notes',
        inverse='_inverse_l10n_fr_pdp_legal_form',
        readonly=False,
        help='Legal form for the #REG# note and BT-33 (for example SARL, SAS).',
    )
    l10n_fr_pdp_share_capital = fields.Float(
        string='Share Capital',
        compute='_compute_l10n_fr_pdp_legal_notes',
        inverse='_inverse_l10n_fr_pdp_share_capital',
        readonly=False,
        help='Share capital in company currency for the #REG# note and BT-33.',
    )
    l10n_fr_pdp_rcs_city = fields.Char(
        string='RCS City',
        compute='_compute_l10n_fr_pdp_legal_notes',
        inverse='_inverse_l10n_fr_pdp_rcs_city',
        readonly=False,
        help='City of the commercial court (greffe) for the #ABL# note.',
    )
    l10n_fr_pdp_peppol_proxy_display_state = fields.Selection(
        selection=[
            ('not_registered', 'Not registered'),
            ('in_verification', 'In verification'),
            ('sender', 'Can send but not receive'),
            ('smp_registration', 'Can send, pending registration to receive'),
            ('receiver', 'Can send and receive'),
            ('rejected', 'Rejected'),
        ],
        string='Approved Platform Status',
        compute='_compute_l10n_fr_pdp_peppol_proxy_display_state',
    )

    def action_open_pdp_form(self):
        registration_wizard = self.env['pdp.registration'].create({'company_id': self.company_id.id})
        return registration_wizard._action_open_pdp_form(reopen=False)

    def action_open_peppol_form(self):
        self.ensure_one()
        if self.country_code != 'FR' and self.account_peppol_eas != '0225':
            return super().action_open_peppol_form()
        return self.action_open_pdp_form()

    @api.depends('company_id.l10n_fr_pdp_pilot_phase')
    def _compute_l10n_fr_pdp_pilot_phase(self):
        for record in self:
            record.l10n_fr_pdp_pilot_phase = record.company_id.l10n_fr_pdp_pilot_phase

    def _inverse_l10n_fr_pdp_pilot_phase(self):
        pass

    @api.depends('company_id')
    def _compute_l10n_fr_pdp_legal_notes(self):
        for settings in self:
            company = settings.company_id
            settings.l10n_fr_pdp_legal_form = company._l10n_fr_pdp_studio_char(STUDIO_LEGAL_FORM)
            settings.l10n_fr_pdp_share_capital = company._l10n_fr_pdp_studio_float(STUDIO_SHARE_CAPITAL)
            settings.l10n_fr_pdp_rcs_city = company._l10n_fr_pdp_studio_char(STUDIO_RCS_CITY)

    def _inverse_l10n_fr_pdp_legal_form(self):
        for settings in self:
            settings.company_id._l10n_fr_pdp_set_studio_value(
                STUDIO_LEGAL_FORM,
                settings.l10n_fr_pdp_legal_form or False,
                ('char', 'text'),
            )

    def _inverse_l10n_fr_pdp_share_capital(self):
        for settings in self:
            settings.company_id._l10n_fr_pdp_set_studio_value(
                STUDIO_SHARE_CAPITAL,
                settings.l10n_fr_pdp_share_capital or 0.0,
                ('float', 'monetary'),
            )

    def _inverse_l10n_fr_pdp_rcs_city(self):
        for settings in self:
            settings.company_id._l10n_fr_pdp_set_studio_value(
                STUDIO_RCS_CITY,
                settings.l10n_fr_pdp_rcs_city or False,
                ('char', 'text'),
            )

    @api.depends('account_peppol_proxy_state')
    def _compute_l10n_fr_pdp_peppol_proxy_display_state(self):
        for record in self:
            record.l10n_fr_pdp_peppol_proxy_display_state = PEPPOL_PROXY_STATE_17_TO_18.get(record.account_peppol_proxy_state) or False

    def _check_mandatory_peppol_user_data(self):
        self.ensure_one()
        if self.company_id._get_peppol_proxy_type() != 'pdp':
            super()._check_mandatory_peppol_user_data()
            return

        if not self.account_peppol_contact_email:
            raise ValidationError(_("A contact email is required."))

    # TODO: remove in master
    @api.model
    def _pdp_ensure_selection_value(self, model_name, field_name, new_value):
        # hack to load new selection values in stable
        field = self.env[model_name]._fields[field_name]
        if new_value not in {value for value, name in field.get_description(self.env)['selection']}:
            self.env['ir.model.fields'].invalidate_model(['selection_ids'])
            self.env['ir.model.fields.selection'].sudo()._update_selection(model_name, field_name, field.selection)
            self.env.registry.clear_cache()
