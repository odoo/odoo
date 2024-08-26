from odoo import Command, api, models
from .extra_eu_tag_map import EXTRA_EU_TAG_MAP
from .extra_eu_tax_map import EXTRA_EU_TAX_MAP


class Company(models.Model):
    _inherit = 'res.company'

    @api.model
    def _map_all_extra_eu_companies_taxes(self):
        ''' Identifies non EU companies that have an oss mapping and calls the _map_extra_eu_taxes function
        '''
        ioss_country_codes = [t[0] for t in EXTRA_EU_TAX_MAP]
        companies = self.search([('account_fiscal_country_id.code', 'in', ioss_country_codes)])
        companies._map_extra_eu_taxes()

    def _map_extra_eu_taxes(self):
        '''Creates or updates Fiscal Positions for each non EU country excluding the company's account_fiscal_country_id
        '''
        ioss_mapping_countries = self.env["res.country"].search([("code", "in", [t[2] for t in EXTRA_EU_TAX_MAP])])
        ioss_tax_groups = self.env['ir.model.data'].search([
            ('module', '=', 'l10n_extra_eu_oss'),
            ('model', '=', 'account.tax.group')])
        for company in self:
            invoice_repartition_lines, refund_repartition_lines = company._get_repartition_lines_ioss()
            taxes = self.env['account.tax'].search([
                ('type_tax_use', '=', 'sale'),
                ('amount_type', '=', 'percent'),
                ('company_id', '=', company.id),
                ('country_id', '=', company.account_fiscal_country_id.id),
                ('tax_group_id', 'not in', ioss_tax_groups.mapped('res_id'))])

            multi_tax_reports_countries_fpos = self.env['account.fiscal.position'].search([
                ('company_id', '=', company.id),
                ('foreign_vat', '!=', False),
            ])
            ioss_countries = ioss_mapping_countries - company.account_fiscal_country_id - multi_tax_reports_countries_fpos.country_id
            for destination_country in ioss_countries:
                mapping = []
                fpos = self.env['account.fiscal.position'].search([
                            ('country_id', '=', destination_country.id),
                            ('company_id', '=', company.id),
                            ('auto_apply', '=', True),
                            ('vat_required', '=', False),
                            ('foreign_vat', '=', False)], limit=1)
                if not fpos:
                    fpos = self.env['account.fiscal.position'].create({
                        'name': f'IOSS B2C {destination_country.name}',
                        'country_id': destination_country.id,
                        'company_id': company.id,
                        'auto_apply': True,
                    })

                foreign_taxes = {tax.amount: tax for tax in fpos.tax_ids.tax_dest_id if tax.amount_type == 'percent'}

                for domestic_tax in taxes:
                    tax_amount = EXTRA_EU_TAX_MAP.get((company.account_fiscal_country_id.code, domestic_tax.amount, destination_country.code), False)
                    if tax_amount and domestic_tax not in fpos.tax_ids.tax_src_id:
                        if not foreign_taxes.get(tax_amount, False):
                            ioss_tax_group_local_xml_id = f"ioss_tax_group_{str(tax_amount).replace('.', '_')}"
                            if not self.env.ref(f"l10n_extra_eu_oss.{ioss_tax_group_local_xml_id}", raise_if_not_found=False):
                                self.env['ir.model.data'].create({
                                    'name': ioss_tax_group_local_xml_id,
                                    'module': 'l10n_extra_eu_oss',
                                    'model': 'account.tax.group',
                                    'res_id': self.env['account.tax.group'].create({'name': f'OSS {tax_amount}%'}).id,
                                    'noupdate': True,
                                })
                            foreign_taxes[tax_amount] = self.env['account.tax'].create({
                                'name': f'{tax_amount}% {destination_country.code} {destination_country.vat_label}',
                                'amount': tax_amount,
                                'invoice_repartition_line_ids': invoice_repartition_lines,
                                'refund_repartition_line_ids': refund_repartition_lines,
                                'type_tax_use': 'sale',
                                'description': f"{tax_amount}%",
                                'tax_group_id': self.env.ref(f'l10n_extra_eu_oss.{ioss_tax_group_local_xml_id}').id,
                                'country_id': company.account_fiscal_country_id.id,
                                'sequence': 1000,
                                'company_id': company.id,
                            })
                        mapping.append((0, 0, {'tax_src_id': domestic_tax.id, 'tax_dest_id': foreign_taxes[tax_amount].id}))
                if mapping:
                    fpos.write({
                        'tax_ids': mapping
                    })

    def _get_repartition_lines_ioss(self):
        self.ensure_one()
        defaults = self.env['account.tax'].with_company(self).default_get(['invoice_repartition_line_ids', 'refund_repartition_line_ids'])
        ioss_account, ioss_tags = self._get_ioss_account(), self._get_ioss_tags()
        base_line, tax_line, vals = 0, 1, 2
        for doc_type in 'invoice', 'refund':
            if ioss_account:
                defaults[f'{doc_type}_repartition_line_ids'][tax_line][vals]['account_id'] = ioss_account.id
            if ioss_tags:
                defaults[f'{doc_type}_repartition_line_ids'][base_line][vals]['tag_ids'] += [Command.link(tag.id) for tag in ioss_tags[f'{doc_type}_base_tag']]
                defaults[f'{doc_type}_repartition_line_ids'][tax_line][vals]['tag_ids'] += [Command.link(tag.id) for tag in ioss_tags[f'{doc_type}_tax_tag']]
        return defaults['invoice_repartition_line_ids'], defaults['refund_repartition_line_ids']

    def _get_ioss_account(self):
        self.ensure_one()
        if not self.env.ref(f'l10n_extra_eu_oss.ioss_tax_account_company_{self.id}', raise_if_not_found=False):
            sales_tax_accounts = self.env['account.tax'].search([
                    ('type_tax_use', '=', 'sale'),
                    ('company_id', '=', self.id)
                ]).invoice_repartition_line_ids.mapped('account_id')
            if not sales_tax_accounts:
                return False
            new_code = self.env['account.account']._search_new_account_code(self, len(sales_tax_accounts[0].code), sales_tax_accounts[0].code[:-2])
            ioss_account = self.env['account.account'].create({
                'name': f'{sales_tax_accounts[0].name} IOSS',
                'code': new_code,
                'user_type_id': sales_tax_accounts[0].user_type_id.id,
                'company_id': self.id,
                'tag_ids': [(4, tag.id, 0) for tag in sales_tax_accounts[0].tag_ids],
                })
            self.env['ir.model.data'].create({
                'name': f'ioss_tax_account_company_{self.id}',
                'module': 'l10n_extra_eu_oss',
                'model': 'account.account',
                'res_id': ioss_account.id,
                'noupdate': True,
                })
        return self.env.ref(f'l10n_extra_eu_oss.ioss_tax_account_company_{self.id}')

    def _get_ioss_tags(self):
        ioss_tag = self.env.ref('l10n_eu_oss.tag_eu_import')
        chart_template_xml_id = ''
        if self.chart_template_id:
            [chart_template_xml_id] = self.chart_template_id.parent_id.get_external_id().values() or self.chart_template_id.get_external_id().values()
        tag_for_country = EXTRA_EU_TAG_MAP.get(chart_template_xml_id, {
            'invoice_base_tag': None,
            'invoice_tax_tag': None,
            'refund_base_tag': None,
            'refund_tax_tag': None,
        })

        mapping = {}
        for repartition_line_key, tag_xml_id in tag_for_country.items():
            tag = self.env.ref(tag_xml_id) if tag_xml_id else self.env['account.account.tag']
            if tag and tag._name == "account.tax.report.line":
                tag = tag.tag_ids.filtered(lambda t: not t.tax_negate)
            mapping[repartition_line_key] = tag + ioss_tag

        return mapping
