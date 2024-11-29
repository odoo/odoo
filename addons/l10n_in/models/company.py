# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
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
    l10n_in_tan = fields.Char(string="TAN", help="Tax Deduction and Collection Account Number")
    l10n_in_is_gst_registered = fields.Boolean(string="Register Under GST")
    l10n_in_tcs = fields.Boolean(string="TCS", inverse='_inverse_l10n_in_tcs')
    l10n_in_tds = fields.Boolean(string="TDS", inverse='_inverse_l10n_in_tds')

    def _inverse_l10n_in_tcs(self):
        for company in self:
            if company.l10n_in_tcs:
                module_installed = self.env['ir.module.module'].search([('name', '=', 'l10n_in_tcs'), ('state', '=', 'installed')])
                if not module_installed:
                    company._l10n_in_install_modules(['l10n_in_tcs'])
                else:
                    company._l10n_in_load_tcs_chart_of_accounts_and_taxes(company)

    def _inverse_l10n_in_tds(self):
        for company in self:
            if company.l10n_in_tds:
                module_installed = self.env['ir.module.module'].search([('name', '=', 'l10n_in_tds'), ('state', '=', 'installed')])
                if not module_installed:
                    company._l10n_in_install_modules(['l10n_in_tds'])
                else:
                    company._l10n_in_load_tds_chart_of_accounts_and_taxes(company)

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

    @api.constrains('l10n_in_is_gst_registered')
    def _check_l10n_in_is_gst_registered(self):
        for record in self:
            if not record.l10n_in_is_gst_registered:
                raise UserError(_('Once GST is enabled, it cannot be disabled.'))

    @api.constrains('l10n_in_tcs')
    def _check_l10n_in_tcs(self):
        for record in self:
            if not record.l10n_in_tcs:
                raise UserError(_('Once TCS is enabled, it cannot be disabled.'))

    @api.constrains('l10n_in_tds')
    def _check_l10n_in_tds(self):
        for record in self:
            if not record.l10n_in_tds:
                raise UserError(_('Once TDS is enabled, it cannot be disabled.'))

    def _l10n_in_install_modules(self, module_names):
        modules_sudo = self.env['ir.module.module'].sudo().search([('name', 'in', module_names)])
        STATES = ['installed', 'to install', 'to upgrade']
        modules_sudo.filtered(lambda m: m.state not in STATES).button_immediate_install()
