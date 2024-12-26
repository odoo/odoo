import pytz
from stdnum.in_ import pan, gstin
from datetime import timedelta, datetime, time

from odoo import _, api, fields, models 
from odoo.exceptions import ValidationError


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
        compute="_compute_l10n_in_hsn_code_digit_and_l10n_in_pan",
        store=True,
        readonly=False,
    )
    l10n_in_edi_production_env = fields.Boolean(
        string="Indian Production Environment",
        help="Enable the use of production credentials",
        groups="base.group_system",
        default=True,
    )
    l10n_in_pan = fields.Char(
        string="PAN",
        compute="_compute_l10n_in_hsn_code_digit_and_l10n_in_pan",
        store=True,
        readonly=False,
        help="PAN enables the department to link all transactions of the person with the department.\n"
             "These transactions include taxpayments, TDS/TCS credits, returns of income/wealth/gift/FBT,"
             "specified transactions, correspondence, and so on.\n"
             "Thus, PAN acts as an identifier for the person with the tax department.",
    )
    l10n_in_pan_type = fields.Char(string="PAN Type", compute="_compute_l10n_in_pan_type")
    l10n_in_gst_state_warning = fields.Char(related="partner_id.l10n_in_gst_state_warning")
    l10n_in_iec_number = fields.Char(string="IEC No.")
    l10n_in_lut_number = fields.Char(string="LUT No.")
    l10n_in_lut_expiration_date = fields.Date(string="LUT valid up to", help="Date until which the LUT is valid.")

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
                company.account_sale_tax_id = self.env['account.chart.template'].with_company(company).ref('sgst_sale_5').id
                company.account_purchase_tax_id = self.env['account.chart.template'].with_company(company).ref('sgst_purchase_5').id

    @api.depends('parent_id.l10n_in_tds_feature', 'parent_id.l10n_in_tcs_feature', 'parent_id.l10n_in_is_gst_registered')
    def _compute_l10n_in_parent_based_features(self):
        for company in self:
            if company.parent_id:
                company.l10n_in_tds_feature = company.parent_id.l10n_in_tds_feature
                company.l10n_in_tcs_feature = company.parent_id.l10n_in_tcs_feature
                company.l10n_in_is_gst_registered = company.parent_id.l10n_in_is_gst_registered

    def _activate_l10n_in_taxes(self, group_refs, company):
        for group_ref in group_refs:
            tax_group_id = self.env['account.chart.template'].with_company(company).ref(group_ref).id
            taxes = self.env['account.tax'].with_company(company).with_context(active_test=False).search([
                ('tax_group_id', '=', tax_group_id),
            ])
            taxes.write({'active': True})

    @api.depends('vat')
    def _compute_l10n_in_hsn_code_digit_and_l10n_in_pan(self):
        for record in self:
            if record.country_code == "IN" and record.vat:
                record.l10n_in_hsn_code_digit = "4"
                record.l10n_in_pan = gstin.to_pan(record.vat) if gstin.is_valid(record.vat) else False
            else:
                record.l10n_in_hsn_code_digit = False
                record.l10n_in_pan = False

    @api.depends('l10n_in_pan')
    def _compute_l10n_in_pan_type(self):
        for record in self:
            if pan.is_valid(record.l10n_in_pan):
                record.l10n_in_pan_type = pan.info(record.l10n_in_pan)['holder_type']
            else:
                record.l10n_in_pan_type = False

    @api.onchange('vat')
    def onchange_vat(self):
        self.partner_id.onchange_vat()

    def _update_l10n_in_export_sez_fiscal_position(self):
        """Update fiscal positions based on LUT and IEC numbers."""
        for company in self:
            ChartTemplate = self.env['account.chart.template'].with_company(company)
            lut_sez_fp = ChartTemplate.ref('fiscal_position_in_lut_sez')
            export_sez_fp = ChartTemplate.ref('fiscal_position_in_export_sez_in')
            if company.l10n_in_iec_number and not export_sez_fp.auto_apply and not company.l10n_in_lut_number:
                export_sez_fp.write({'auto_apply': True})
            elif export_sez_fp.auto_apply:
                export_sez_fp.write({'auto_apply': False})

            if company.l10n_in_lut_number and company.l10n_in_lut_expiration_date:
                if not lut_sez_fp.auto_apply:
                    lut_sez_fp.write({'auto_apply': True})
                    export_sez_fp.write({'auto_apply': False})
                user_tz = pytz.timezone(self.env.user.tz)
                lut_cron_trigger_datetime = user_tz.localize(datetime.combine(company.l10n_in_lut_expiration_date + timedelta(days=1), time.min))
                self.env.ref('l10n_in.ir_cron_update_lut_status')._trigger((lut_cron_trigger_datetime.astimezone(pytz.utc)).replace(tzinfo=None))
            elif lut_sez_fp.auto_apply:
                lut_sez_fp.write({'auto_apply': False})

    @api.constrains('l10n_in_pan')
    def _check_l10n_in_pan(self):
        for record in self:
            if record.l10n_in_pan and not pan.is_valid(record.l10n_in_pan):
                raise ValidationError(_('The entered PAN seems invalid. Please enter a valid PAN.'))

    @api.constrains('l10n_in_lut_expiration_date')
    def _check_l10n_in_lut_expiration_date(self):
        if self.l10n_in_lut_expiration_date and self.l10n_in_lut_expiration_date < fields.Date.today():
            raise ValidationError(_('Please enter a valid LUT Expiration Date.'))

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
        if 'l10n_in_iec_number' in vals or 'l10n_in_lut_number' in vals or vals.get('l10n_in_lut_expiration_date'):
            self._update_l10n_in_export_sez_fiscal_position()
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

    def _cron_update_lut_status(self):
        """Schedule the cron job to deactivate LUT after expiration."""
        tz = pytz.timezone("Asia/Kolkata")
        today_date = fields.Datetime.now().astimezone(tz).replace(tzinfo=None).date()
        companies = self.search([
            ('l10n_in_lut_number', '!=', False),
            ('l10n_in_lut_expiration_date', '<', today_date),
        ])
        for company in companies:
            company.write({'l10n_in_lut_number': False, 'l10n_in_lut_expiration_date': False})
            company._update_l10n_in_export_sez_fiscal_position()
