from odoo import Command, api, fields, models


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
    l10n_in_withholding_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string="TDS Journal",
        check_company=True,
    )

    # GST settings
    l10n_in_gst_registration_type = fields.Selection(
        selection=[
            ('regular', 'Regular Scheme'),
            ('composition', 'Composition Scheme'),
        ],
        compute="_compute_l10n_in_parent_based_features",
        inverse="_inverse_l10n_in_gst_registration_type",
        string="GST Registration Type",
        store=True,
        recursive=True,
    )
    l10n_in_composition_tax_rate = fields.Selection(
        selection=[
            ('1', '1% for Manufacturers and Traders'),
            ('5', '5% for Restaurants'),
            ('6', '6% for Service Providers'),
        ],
        string="Composition Tax Rate"
    )
    l10n_in_gstin_status_feature = fields.Boolean(string="Check GST Number Status")
    l10n_in_disable_b2c_hsn_reporting = fields.Boolean(string="Disable B2C HSN Reporting")

    def _get_gst_group_refs(self):
        return [
            'sgst_group',
            'cgst_group',
            'igst_group',
            'cess_group',
            'gst_group',
            'exempt_group',
            'nil_rated_group',
            'non_gst_supplies_group',
        ]

    @api.depends('l10n_in_upi_id')
    def _compute_qr_code(self):
        # EXTENDS 'account'
        indian_companies = self.filtered(lambda c: c.country_code == 'IN')
        for company in indian_companies:
            company.qr_code = bool(company.l10n_in_upi_id)
        super(ResCompany, self - indian_companies)._compute_qr_code()

    def _inverse_l10n_in_tds_feature(self):
        for company in self:
            self._activate_l10n_in_taxes(['tds_it_act_25_group'], company, company.l10n_in_tds_feature)

    def _inverse_l10n_in_tcs_feature(self):
        for company in self:
            self._activate_l10n_in_taxes(['tcs_it_act_25_group'], company, company.l10n_in_tcs_feature)

    def _inverse_l10n_in_gst_registration_type(self):
        for company in self:
            gst_group_refs = self._get_gst_group_refs()
            self._activate_l10n_in_taxes(gst_group_refs, company, False)
            if company.l10n_in_gst_registration_type:
                self._activate_l10n_in_taxes(gst_group_refs, company, True)
                # Set sale and purchase tax accounts when user registered under GST.
                ChartTemplate = self.env['account.chart.template'].with_company(company)
                if company.l10n_in_gst_registration_type == 'regular':
                    company.account_sale_tax_id = ChartTemplate.ref('sgst_sale_5', raise_if_not_found=False)
                    company.account_purchase_tax_id = ChartTemplate.ref('sgst_purchase_5', raise_if_not_found=False)
                elif company.l10n_in_gst_registration_type == 'composition':
                    company.account_sale_tax_id = False
                    company.account_purchase_tax_id = ChartTemplate.ref('sgst_purchase_5_composition', raise_if_not_found=False)
            else:
                company.account_sale_tax_id = False
                company.account_purchase_tax_id = False

    @api.depends('country_code', 'root_id')
    def _compute_force_restrictive_audit_trail(self):
        super()._compute_force_restrictive_audit_trail()
        for company in self:
            if company.country_code == 'IN':
                company.force_restrictive_audit_trail = company.root_id._existing_accounting()

    @api.depends('parent_id.l10n_in_tds_feature', 'parent_id.l10n_in_tcs_feature', 'parent_id.l10n_in_gst_registration_type')
    def _compute_l10n_in_parent_based_features(self):
        for company in self:
            if company.parent_id:
                company.l10n_in_tds_feature = company.parent_id.l10n_in_tds_feature
                company.l10n_in_tcs_feature = company.parent_id.l10n_in_tcs_feature
                company.l10n_in_gst_registration_type = company.parent_id.l10n_in_gst_registration_type

    def _activate_l10n_in_taxes(self, group_refs, company, active=True):
        ChartTemplate = self.env['account.chart.template'].with_company(company)
        tax_group_ids = [
            tax_group.id
            for group_ref in group_refs
            if (tax_group := ChartTemplate.ref(group_ref, raise_if_not_found=False))
        ]

        if tax_group_ids:
            domain = [
                ('tax_group_id', 'in', tax_group_ids),
                ('active', '!=', active),
            ]
            is_gst_group = bool(set(self._get_gst_group_refs()).intersection(group_refs))
            if active and company.l10n_in_gst_registration_type and is_gst_group:
                composition_tax_ids = self.env['ir.model.data'].search([
                    ('model', '=', 'account.tax'),
                    ('module', '=', 'account'),
                    ('name', '=like', f'{company.id}_%_purchase_%_composition'),
                ]).mapped('res_id')
                if company.l10n_in_gst_registration_type == 'regular':
                    domain += [('id', 'not in', composition_tax_ids)]
                elif company.l10n_in_gst_registration_type == 'composition':
                    domain += [
                        '|', '|', '&',
                        ('type_tax_use', '=', 'purchase'),
                        ('l10n_in_reverse_charge', '=', True),
                        ('id', 'in', composition_tax_ids),
                        ('l10n_in_tax_type', 'in', ['nil_rated', 'exempt', 'non_gst']),
                    ]
            taxes = self.env['account.tax'].with_company(company).with_context(active_test=False).search(domain)
            taxes.write({'active': active})

    @api.depends('has_vat')
    def _compute_l10n_in_hsn_code_digit(self):
        for record in self:
            if record.country_code == "IN" and record.has_vat:
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
        if vals.get('state_id') or vals.get('country_id'):
            # Update Fiscal Positions for companies setting up state for the first time
            self._update_l10n_in_fiscal_position()
        return res

    def _update_l10n_in_fiscal_position(self):
        companies_need_update_fp = self.filtered(lambda c: (c.parent_ids[0].chart_template or '').startswith('in'))
        for company in companies_need_update_fp:
            ChartTemplate = self.env['account.chart.template'].with_company(company)
            fiscal_position_data = ChartTemplate._get_in_account_fiscal_position()
            for values in fiscal_position_data.values():
                values['tax_ids'] = [Command.set([
                    xml_id
                    for xml_id in values['tax_ids'][0][2]
                    if ChartTemplate.ref(xml_id, raise_if_not_found=False)
                ])]
            ChartTemplate._load_data({'account.fiscal.position': fiscal_position_data})

    def _update_l10n_in_gst_registration_type(self):
        for company in self:
            if company.country_code == "IN" and company.vat and not company.l10n_in_gst_registration_type and company.id in self.env.user._get_company_ids():
                company.l10n_in_gst_registration_type = 'regular' if company.partner_id.check_vat_in(company.vat) else False

    def action_update_state_as_per_gstin(self):
        self.ensure_one()
        self.partner_id.action_update_state_as_per_gstin()
