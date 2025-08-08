import pytz
from stdnum.in_ import pan, gstin

from odoo import _, api, fields, models 
from odoo.exceptions import RedirectWarning


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_in_upi_id = fields.Char(string="UPI Id")
    l10n_in_hsn_code_digit = fields.Selection(
        selection=[
            ("4", "4 Digits (turnover < 5 CR.)"),
            ("6", "6 Digits (turnover > 5 CR.)"),
            ("8", "8 Digits"),
        ],
        string="HSN Code Digit",
        compute="_compute_l10n_in_hsn_code_digit",
        store=True,
        readonly=False,
    )
    l10n_in_edi_production_env = fields.Boolean(
        string="Indian Production Environment",
        help="Enable the use of production credentials",
        groups="base.group_system",
        default=True,
    )
    l10n_in_pan_entity_id = fields.Many2one(
        related="partner_id.l10n_in_pan_entity_id",
        string="PAN",
        store=True,
        readonly=False,
        help="PAN enables the department to link all transactions of the person with the department.\n"
             "These transactions include taxpayments, TDS/TCS credits, returns of income/wealth/gift/FBT,"
             "specified transactions, correspondence, and so on.\n"
             "Thus, PAN acts as an identifier for the person with the tax department.",
    )
    l10n_in_pan_type = fields.Selection(related="l10n_in_pan_entity_id.type", string="PAN Type")
    l10n_in_tan = fields.Char(related="partner_id.l10n_in_tan", string="TAN", readonly=False)
    l10n_in_gst_state_warning = fields.Char(related="partner_id.l10n_in_gst_state_warning")

    # TDS/TCS settings
    l10n_in_tds_feature = fields.Boolean(
        string="TDS",
        compute="_compute_l10n_in_parent_based_features",
        inverse="_inverse_l10n_in_tds_feature",
        recursive=True,
        store=True,
    )
    l10n_in_tcs_feature = fields.Boolean(
        string="TCS",
        compute="_compute_l10n_in_parent_based_features",
        inverse="_inverse_l10n_in_tcs_feature",
        recursive=True,
        store=True,
    )
    l10n_in_withholding_account_id = fields.Many2one(
        comodel_name='account.account',
        string="TDS Account",
        check_company=True,
    )
    l10n_in_withholding_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="TDS Journal",
        check_company=True,
    )

    # GST settings
    l10n_in_is_gst_registered = fields.Boolean(
        string="Registered Under GST",
        compute="_compute_l10n_in_parent_based_features",
        inverse="_inverse_l10n_in_is_gst_registered",
        recursive=True,
        store=True,
    )
    l10n_in_gstin_status_feature = fields.Boolean(string="Check GST Number Status")

    def _inverse_l10n_in_tds_feature(self):
        for company in self:
            if company.l10n_in_tds_feature:
                self._activate_l10n_in_taxes(['tds_group'], company)

    def _inverse_l10n_in_tcs_feature(self):
        for company in self:
            if company.l10n_in_tcs_feature:
                self._activate_l10n_in_taxes(['tcs_group'], company)

    def _inverse_l10n_in_is_gst_registered(self):
        for company in self:
            if company.l10n_in_is_gst_registered:
                gst_group_refs = [
                    'sgst_group',
                    'cgst_group',
                    'igst_group',
                    'cess_group',
                    'gst_group',
                    'exempt_group',
                    'nil_rated_group',
                    'non_gst_supplies_group',
                ]
                self._activate_l10n_in_taxes(gst_group_refs, company)
                # Set sale and purchase tax accounts when user registered under GST.
                company.account_sale_tax_id = self.env['account.chart.template'].with_company(company).ref('sgst_sale_5', raise_if_not_found=False)
                company.account_purchase_tax_id = self.env['account.chart.template'].with_company(company).ref('sgst_purchase_5', raise_if_not_found=False)

    @api.depends('parent_id.l10n_in_tds_feature', 'parent_id.l10n_in_tcs_feature', 'parent_id.l10n_in_is_gst_registered')
    def _compute_l10n_in_parent_based_features(self):
        for company in self:
            if company.parent_id:
                company.l10n_in_tds_feature = company.parent_id.l10n_in_tds_feature
                company.l10n_in_tcs_feature = company.parent_id.l10n_in_tcs_feature
                company.l10n_in_is_gst_registered = company.parent_id.l10n_in_is_gst_registered

    def _activate_l10n_in_taxes(self, group_refs, company):
        for group_ref in group_refs:
            tax_group = self.env['account.chart.template'].with_company(company).ref(group_ref, raise_if_not_found=False)
            if not tax_group:
                continue
            taxes = self.env['account.tax'].with_company(company).with_context(active_test=False).search([
                ('tax_group_id', '=', tax_group.id),
            ])
            taxes.write({'active': True})

    @api.depends('vat')
    def _compute_l10n_in_hsn_code_digit(self):
        for record in self:
            if record.country_code == "IN" and record.vat:
                record.l10n_in_hsn_code_digit = "4"
            else:
                record.l10n_in_hsn_code_digit = False

    @api.onchange('vat')
    def onchange_vat(self):
        self.partner_id.onchange_vat()

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        # Update Fiscal Positions for new branch
        res._update_l10n_in_fiscal_position()
        return res

    def write(self, vals):
        res = super().write(vals)
        if vals.get('vat'):
            # Enable GST(l10n_in_is_gst_registered) when a valid GSTIN(vat) is applied.
            self._update_l10n_in_is_gst_registered()
        if (vals.get('state_id') or vals.get('country_id')) and not self.env.context.get('delay_account_group_sync'):
            # Update Fiscal Positions for companies setting up state for the first time
            self._update_l10n_in_fiscal_position()
        return res

    def _update_l10n_in_fiscal_position(self):
        companies_need_update_fp = self.filtered(lambda c: c.parent_ids[0].chart_template == 'in')
        for company in companies_need_update_fp:
            ChartTemplate = self.env['account.chart.template'].with_company(company)
            fiscal_position_data = ChartTemplate._get_in_account_fiscal_position()
            ChartTemplate._load_data({'account.fiscal.position': fiscal_position_data})

    def _update_l10n_in_is_gst_registered(self):
        for company in self:
            if company.country_code == "IN" and company.vat:
                company.l10n_in_is_gst_registered = company.partner_id.check_vat_in(company.vat)

    def action_update_state_as_per_gstin(self):
        self.ensure_one()
        self.partner_id.action_update_state_as_per_gstin()

    def _check_tax_return_configuration(self):
        """
        Check if the company is properly configured for tax returns.
        :raises RedirectWarning: if something is wrong configured.
        """

        if self.country_code != 'IN':
            return super()._check_tax_return_configuration()

        is_l10n_in_reports_installed = 'l10n_in_reports' in self.env['ir.module.module']._installed()
        if not is_l10n_in_reports_installed:
            msg = _("First enable GST e-Filing feature from configuration for company %s.", (self.name))
            action = self.env.ref("account.action_account_config")
            raise RedirectWarning(msg, action.id, _('Go to configuration'))
