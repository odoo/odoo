# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_fr_siret = fields.Char(related='partner_id.l10n_fr_siret', readonly=False)
    l10n_fr_siren = fields.Char(related='partner_id.l10n_fr_siren', readonly=False)
    l10n_fr_rounding_difference_loss_account_id = fields.Many2one('account.account', check_company=True)
    l10n_fr_rounding_difference_profit_account_id = fields.Many2one('account.account', check_company=True)

    def _get_default_vat_disabled_tax(self):
        self.ensure_one()
        if self.account_fiscal_country_id.code != 'FR':
            return super()._get_default_vat_disabled_tax()
        return self._get_or_create_chart_template_record('account.tax', 'tva_sale_non_assujetti_0_biens', {})

    def _inverse_vat_disabled(self):
        super()._inverse_vat_disabled()
        for company in self.filtered(lambda c: c.vat_disabled_available and c.account_fiscal_country_id.code == 'FR' and c.chart_template):
            ChartTemplate = company.env['account.chart.template'].with_company(company)
            chart_template_data = ChartTemplate._get_chart_template_data(company.chart_template)

            no_subject_to_vat_fp = self._get_or_create_chart_template_record('account.fiscal.position', 'fiscal_position_template_no_vat', chart_template_data)
            fps_to_toggle = self.env['account.fiscal.position'].with_context(active_test=False).search([
                ('company_id', '=', company.id),
                *([('id', '!=', no_subject_to_vat_fp.id)] if no_subject_to_vat_fp else []),
            ])
            fps_to_toggle.active = not company.vat_disabled
            if no_subject_to_vat_fp:
                no_subject_to_vat_fp.active = company.vat_disabled
                no_subject_to_vat_fp.tax_ids.active = company.vat_disabled

            company_data = chart_template_data['res.company'][company.id]
            default_purchase_tax = self._get_or_create_chart_template_record('account.tax', company_data['account_purchase_tax_id'], chart_template_data)
            purchase_vat_disabled = {
                20: ('tva_sale_non_assujetti_0', 'tva_purchase_na_normale', 'tva_purchase_na_normale_biens'),
                10: ('tva_purchase_na_intermediaire', 'tva_purchase_na_intermediaire_biens'),
                5.5: ('tva_purchase_na_reduite', 'tva_purchase_na_reduite_biens'),
                2.1: ('tva_purchase_na_super_reduite', 'tva_purchase_na_super_reduite_biens'),
            }
            vat_disabled_taxes = self.env['account.tax']
            for tax_amount, xml_ids in purchase_vat_disabled.items():
                for tax_xml_id in xml_ids:
                    tax = self._get_or_create_chart_template_record('account.tax', tax_xml_id, chart_template_data)
                    tax.original_tax_ids = self.env['account.tax'].with_context(active_test=False).search([
                        *self.env['account.tax']._check_company_domain(company),
                        ('type_tax_use', '=', tax.type_tax_use),
                        ('tax_scope', '=', tax.tax_scope),
                        ('amount', '=', tax_amount),
                        ('id', '!=', tax.id),
                    ])
                    vat_disabled_taxes += tax
            vat_disabled_taxes.active = company.vat_disabled
            company.account_purchase_tax_id = (
                self._get_or_create_chart_template_record('account.tax', 'tva_purchase_na_normale_biens', chart_template_data)
                if company.vat_disabled else default_purchase_tax
            )
