from odoo import models


def _get_or_create_chart_template_record(company, model, xmlid, chart_template_data=None):
    ChartTemplate = company.env['account.chart.template'].with_company(company)
    record = ChartTemplate.ref(xmlid, raise_if_not_found=False) or company.env[model]
    if record or not company.chart_template:
        return record
    if not chart_template_data:
        chart_template_data = ChartTemplate._get_chart_template_data(company.chart_template)
    record_data = chart_template_data[model].get(xmlid)
    if not record_data:
        return record
    created_records = ChartTemplate._load_data({model: {xmlid: record_data}}) or {}
    return created_records.get(model) or company.env[model]


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _get_default_vat_disabled_tax(self):
        self.ensure_one()
        if self.account_fiscal_country_id.code != 'BE':
            return super()._get_default_vat_disabled_tax()
        return _get_or_create_chart_template_record(self, 'account.tax', 'attn_VAT-OUT-00-NA-S', {})

    def _inverse_vat_disabled(self):
        super()._inverse_vat_disabled()
        for company in self.filtered(lambda c: c.vat_disabled_available and c.account_fiscal_country_id.code == 'BE' and c.chart_template):
            ChartTemplate = company.env['account.chart.template'].with_company(company)
            chart_template_data = ChartTemplate._get_chart_template_data(company.chart_template)

            no_subject_to_vat_fp = _get_or_create_chart_template_record(company, 'account.fiscal.position', 'fiscal_position_template_7', chart_template_data)
            fps_to_toggle = self.env['account.fiscal.position'].with_context(active_test=False).search([
                ('company_id', '=', company.id),
                *([('id', '!=', no_subject_to_vat_fp.id)] if no_subject_to_vat_fp else []),
            ])
            fps_to_toggle.active = not company.vat_disabled
            if no_subject_to_vat_fp:
                no_subject_to_vat_fp.active = company.vat_disabled
                no_subject_to_vat_fp.tax_ids.active = company.vat_disabled

            company_data = chart_template_data['res.company'][company.id]
            default_purchase_tax = _get_or_create_chart_template_record(company, 'account.tax', company_data['account_purchase_tax_id'], chart_template_data)
            vat_disabled_purchase_21 = _get_or_create_chart_template_record(company, 'account.tax', 'attn_VAT-IN-21-ND', chart_template_data)
            vat_disabled_purchase_12 = _get_or_create_chart_template_record(company, 'account.tax', 'attn_VAT-IN-12-ND', chart_template_data)
            vat_disabled_purchase_06 = _get_or_create_chart_template_record(company, 'account.tax', 'attn_VAT-IN-06-ND', chart_template_data)
            vat_disabled_purchase_00 = _get_or_create_chart_template_record(company, 'account.tax', 'attn_VAT-IN-00-ND', chart_template_data)
            vat_disabled_purchase_taxes = vat_disabled_purchase_21 | vat_disabled_purchase_12 | vat_disabled_purchase_06 | vat_disabled_purchase_00
            replaced_taxes = self.env['account.tax'].with_context(active_test=False)._read_group([
                *self.env['account.tax']._check_company_domain(company),
                ('type_tax_use', '=', 'purchase'),
                ('amount', 'in', [21, 12, 6, 0]),
                ('id', 'not in', vat_disabled_purchase_taxes.ids),
            ], groupby=['amount'], aggregates=['id:recordset'])
            replaced_taxes_per_amount = dict(replaced_taxes)
            vat_disabled_purchase_21.original_tax_ids = replaced_taxes_per_amount.get(21)
            vat_disabled_purchase_12.original_tax_ids = replaced_taxes_per_amount.get(12)
            vat_disabled_purchase_06.original_tax_ids = replaced_taxes_per_amount.get(6)
            vat_disabled_purchase_00.original_tax_ids = replaced_taxes_per_amount.get(0)

            if company.vat_disabled:
                company.account_purchase_receipt_fiscal_position_id = no_subject_to_vat_fp
            else:
                company.account_purchase_receipt_fiscal_position_id = _get_or_create_chart_template_record(company, 'account.fiscal.position', company_data['account_purchase_receipt_fiscal_position_id'], chart_template_data)
            vat_disabled_purchase_taxes.active = company.vat_disabled
            company.account_purchase_tax_id = vat_disabled_purchase_21 if company.vat_disabled else default_purchase_tax
