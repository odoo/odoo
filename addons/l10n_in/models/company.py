# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from stdnum.in_ import pan, gstin


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

    # TDS/TCS settings
    l10n_in_tds_feature = fields.Boolean(string="TDS", inverse="_inverse_l10n_in_tds_feature")
    l10n_in_tcs_feature = fields.Boolean(string="TCS", inverse="_inverse_l10n_in_tcs_feature")
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
    l10n_in_tan = fields.Char(string="TAN", help="Tax Deduction and Collection Account Number")

    # GST settings
    l10n_in_is_gst_registered = fields.Boolean(string="Registered Under GST", inverse="_inverse_l10n_in_is_gst_registered")
    l10n_in_gstin_status_feature = fields.Boolean(string="Check GST Number Status")
    l10n_in_gst_efiling_feature = fields.Boolean(string="GST E-Filing & Matching Feature")
    l10n_in_fetch_vendor_edi_feature = fields.Boolean(string="Fetch Vendor E-Invoiced Document")

    # E-Invoice
    l10n_in_edi_feature = fields.Boolean(string="E-Invoicing")
    # E-Waybill
    l10n_in_ewaybill_feature = fields.Boolean(string="E-Way bill")
    # ENet Batch Payment
    l10n_in_enet_vendor_batch_payment_feature = fields.Boolean(string="ENet Vendor Batch Payment")

    def _inverse_l10n_in_tds_feature(self):
        for company in self:
            if company.l10n_in_tds_feature:
                tds_group_id = self.env['account.chart.template'].ref('tds_group').id
                tds_taxes = self.env['account.tax'].with_context(active_test=False).search([('tax_group_id', '=', tds_group_id)])
                tds_taxes.write({'active': True})
            if company.child_ids:
                company.child_ids.write({'l10n_in_tds_feature': company.l10n_in_tds_feature})

    def _inverse_l10n_in_tcs_feature(self):
        for company in self:
            if company.l10n_in_tcs_feature:
                tcs_group_id = self.env['account.chart.template'].ref('tcs_group').id
                tcs_taxes = self.env['account.tax'].with_context(active_test=False).search([('tax_group_id', '=', tcs_group_id)])
                tcs_taxes.write({'active': True})
            if company.child_ids:
                company.child_ids.write({'l10n_in_tcs_feature': company.l10n_in_tcs_feature})

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
                for ref in gst_group_refs:
                    gst_group_id = self.env['account.chart.template'].ref(ref).id
                    gst_taxes = self.env['account.tax'].with_context(active_test=False).search([
                        ('tax_group_id', '=', gst_group_id)
                    ])
                    gst_taxes.write({'active': True})
                # Set sale and purchase tax accounts when user registered under GST.
                company.account_sale_tax_id = self.env['account.chart.template'].ref('sgst_sale_5').id
                company.account_purchase_tax_id = self.env['account.chart.template'].ref('sgst_purchase_5').id
            if company.child_ids:
                company.child_ids.write({'l10n_in_is_gst_registered': company.l10n_in_is_gst_registered})

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

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        # Update Fiscal Positions for new branch
        res._update_l10n_in_fiscal_position()
        return res

    def write(self, vals):
        res = super().write(vals)
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

    @api.constrains('l10n_in_pan')
    def _check_l10n_in_pan(self):
        for record in self:
            if record.l10n_in_pan and not pan.is_valid(record.l10n_in_pan):
                raise ValidationError(_('The entered PAN seems invalid. Please enter a valid PAN.'))

    def action_update_state_as_per_gstin(self):
        self.ensure_one()
        self.partner_id.action_update_state_as_per_gstin()
