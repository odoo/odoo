# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.addons.account.models.chart_template import template
from odoo.exceptions import UserError


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('es_general')
    def _get_es_general_template_data(self, template_code=None):
        return {
            'name': _('Plan General (Dinámico)'),
            'parent': 'es_common',
            'visible': True,
        }

    @template('es_general', 'res.company')
    def _get_es_general_res_company(self):
        tax_plan = self.env.company.l10n_es_tax_plan
        if tax_plan == 'igic':
            return {
                self.env.company.id: {
                    'account_sale_tax_id': 'account_tax_template_igic_r_7',
                    'account_purchase_tax_id': 'account_tax_template_igic_sop_7',
                },
            }
        return {
            self.env.company.id: {
                'account_sale_tax_id': 'account_tax_template_s_iva21b',
                'account_purchase_tax_id': 'account_tax_template_p_iva21_bc',
            },
        }

    @template('es_general', 'account.tax')
    def _get_es_general_account_tax(self, template_code=None):
        tax_plan = self.env.company.l10n_es_tax_plan
        base_csv = 'es_canary_common' if tax_plan == 'igic' else 'es_common_mainland'
        tax_data = self._parse_csv(base_csv, 'account.tax', module='l10n_es')

        try:
            self._deref_account_tags('es_general', tax_data)
        except KeyError as e:
            raise UserError(_(
                "Error in template 'es_general': Could not perform tax tag mapping. "
                "Make sure the template is correctly registered and visible. "
                "Technical detail: %s", e
            ))
        except Exception as e:  # noqa: BLE001
            raise UserError(_(
                "Unexpected error while loading taxes for 'es_general': %s", e
            ))

        return tax_data

    @template('es_general', 'account.account')
    def _get_es_general_account_account(self, template_code=None):
        company = self.env.company
        chart_type = company.l10n_es_general_chart_type
        tax_plan = company.l10n_es_tax_plan

        base_csv = 'es_canary_common' if tax_plan == 'igic' else 'es_common_mainland'
        accounts = self._parse_csv(base_csv, 'account.account', module='l10n_es')

        if chart_type in ('full', 'abbreviated'):
            plan_accounts = self._parse_csv('es_full', 'account.account', module='l10n_es')
        elif chart_type == 'smes':
            plan_accounts = self._parse_csv('es_pymes', 'account.account', module='l10n_es')
        else:
            plan_accounts = {}

        if tax_plan == 'igic':
            for data in plan_accounts.values():
                data.pop('tax_ids', None)

        accounts.update(plan_accounts)
        return accounts

    def _l10n_es_manage_dynamic_accounts(self, company):
        chart_type = company.l10n_es_general_chart_type

        self.with_company(company).try_loading('es_general', company=company, install_demo=False)

        code_digits = 6

        full_data = self._parse_csv('es_full', 'account.account', module='l10n_es')
        full_codes = {vals['code'].ljust(code_digits, '0') for vals in full_data.values() if 'code' in vals}

        smes_data = self._parse_csv('es_pymes', 'account.account', module='l10n_es')
        smes_codes = {vals['code'].ljust(code_digits, '0') for vals in smes_data.values() if 'code' in vals}

        only_full_accounts = list(full_codes - smes_codes)
        only_smes_accounts = list(smes_codes - full_codes)

        to_archive_accounts = self.env['account.account']
        to_activate_accounts = self.env['account.account']

        if chart_type in ('full', 'abbreviated'):
            to_activate_accounts = self.env['account.account'].with_context(active_test=False).search(
                    [('code', 'in', only_full_accounts),
                    ('company_ids', 'in', company.id)])
            to_archive_accounts = self.env['account.account'].with_context(active_test=False).search(
                [('code', 'in', only_smes_accounts),
                ('company_ids', 'in', company.id)])

        if chart_type == "smes":
            to_activate_accounts = self.env['account.account'].with_context(active_test=False).search(
                    [('code', 'in', only_smes_accounts),
                    ('company_ids', 'in', company.id)])
            to_archive_accounts = self.env['account.account'].with_context(active_test=False).search(
                [('code', 'in', only_full_accounts),
                ('company_ids', 'in', company.id)])

        if to_activate_accounts:
            to_activate_accounts.write({'active': True})
        if to_archive_accounts:
            to_archive_accounts.write({'active': False})

    def _l10n_es_manage_dynamic_taxes(self, company):

        tax_plan = company.l10n_es_tax_plan
        mainland_taxes = self._parse_csv('es_common_mainland', 'account.tax', module='l10n_es')
        mainland_ids = list(mainland_taxes.keys())
        canary_taxes = self._parse_csv('es_canary_common', 'account.tax', module='l10n_es')
        canary_ids = list(canary_taxes.keys())

        def get_taxes(xml_ids):
            taxes = self.env['account.tax']
            for xml_id in xml_ids:
                tax = self.ref(xml_id, raise_if_not_found=False)
                if tax:
                    taxes |= tax
            return taxes

        if tax_plan == 'igic':
            to_activate = get_taxes(canary_ids)
            to_archive = get_taxes(mainland_ids)
        else:
            to_activate = get_taxes(mainland_ids)
            to_archive = get_taxes(canary_ids)

        if to_activate:
            to_activate.write({'active': True})
        if to_archive:
            to_archive.write({'active': False})
