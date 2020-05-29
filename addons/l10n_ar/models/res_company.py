# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class ResCompany(models.Model):

    _inherit = "res.company"

    l10n_ar_gross_income_number = fields.Char(
        related='partner_id.l10n_ar_gross_income_number', string='Gross Income Number', readonly=False,
        help="This field is required in order to print the invoice report properly")
    l10n_ar_gross_income_type = fields.Selection(
        related='partner_id.l10n_ar_gross_income_type', string='Gross Income', readonly=False,
        help="This field is required in order to print the invoice report properly")
    l10n_ar_afip_responsibility_type_id = fields.Many2one(
        domain="[('code', 'in', [1, 4, 6])]", related='partner_id.l10n_ar_afip_responsibility_type_id', readonly=False)
    l10n_ar_company_requires_vat = fields.Boolean(compute='_compute_l10n_ar_company_requires_vat', string='Company Requires Vat?')
    l10n_ar_afip_start_date = fields.Date('Activities Start Date')

    @api.onchange('country_id')
    def onchange_country(self):
        """ Argentinian companies use round_globally as tax_calculation_rounding_method """
        for rec in self.filtered(lambda x: x.country_id == self.env.ref('base.ar')):
            rec.tax_calculation_rounding_method = 'round_globally'

    @api.depends('l10n_ar_afip_responsibility_type_id')
    def _compute_l10n_ar_company_requires_vat(self):
        recs_requires_vat = self.filtered(lambda x: x.l10n_ar_afip_responsibility_type_id.code == '1')
        recs_requires_vat.l10n_ar_company_requires_vat = True
        remaining = self - recs_requires_vat
        remaining.l10n_ar_company_requires_vat = False

    def _localization_use_documents(self):
        """ Argentinian localization use documents """
        self.ensure_one()
        return True if self.country_id == self.env.ref('base.ar') else super()._localization_use_documents()

    @api.constrains('l10n_ar_afip_responsibility_type_id')
    def _check_accounting_info(self):
        """ Do not let to change the AFIP Responsibility of the company if there is already installed a chart of
        account and if there has accounting entries """
        if self.env['account.chart.template'].existing_accounting(self):
            raise ValidationError(_(
                'Could not change the AFIP Responsibility of this company because there are already accounting entries.'))

    def _load_or_install_coa(self, modules, module_list):
        """
            load COA only when company have AFIP Responsibility
            because here three COA and it's depend on AFIP Responsibility so we don't wont to load wrong COA for company.
        """
        if not modules and 'l10n_ar' in module_list:
            if self.l10n_ar_afip_responsibility_type_id:
                chart_template_xml_ids = self.env['ir.model.data'].search([('module', 'in', module_list), ('model', '=', 'account.chart.template')])
                chart_templates = self.env['account.chart.template'].browse(chart_template_xml_ids.mapped('res_id'))
                chart_template = chart_templates.filtered(lambda coa: coa._get_ar_responsibility_match(coa.id) == self.l10n_ar_afip_responsibility_type_id)
                chart_template.try_loading(company=self)
        else:
            super()._load_or_install_coa(modules, module_list)
