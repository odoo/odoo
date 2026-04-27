# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.addons.l10n_eu_oss.models.eu_tax_map import EU_TAX_MAP
from odoo.exceptions import UserError

from collections import defaultdict
from lxml import etree, objectify
from dateutil.relativedelta import relativedelta


class OSSTaxReportCustomHandlerOss(models.AbstractModel):
    _name = 'l10n_eu_oss.tax.report.handler'
    _inherit = 'account.generic.tax.report.handler'
    _description = 'OSS Tax Report Custom Handler'

    def _get_vat_closing_entry_additional_domain(self):
        return [
            *self._get_oss_custom_domain(),
            ('tax_line_id', '!=', False),
        ]

    def _get_oss_custom_domain(self):
        """
        To be overridden by OSS specific reports
        Return a custom domain for the oss report
        """
        return []

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        """ The country for OSS taxes can't easily be guessed from SQL, as it would create JOIN issues.
        So, instead of handling them as a grouping key in the tax report engine, we
        post process the result of a grouping made by (type_tax_use, id) to inject the
        grouping by country.
        """
        def append_country_and_taxes_lines(parent_line, rslt, tax_lines_by_country):
            for country, tax_lines in sorted(tax_lines_by_country.items(), key=lambda elem: elem[0].display_name):
                country_columns = []
                for i, column in enumerate(options['columns']):
                    expr_label = column.get('expression_label')

                    if expr_label == 'net':
                        col_value = ''

                    if expr_label == 'tax':
                        col_value = sum(tax_line['columns'][i]['no_format'] for tax_line in tax_lines)

                    country_columns.append(report._build_column_dict(col_value, column, options=options))

                country_line_id = report._get_generic_line_id('res.country', country.id, parent_line_id=parent_line['id'])
                country_line = {
                    'id': country_line_id,
                    'name': country.display_name,
                    'parent_id': parent_line['id'],
                    'columns': country_columns,
                    'unfoldable': False,
                    'level': 2,
                }

                rslt.append((0, country_line))

                for tax_line in tax_lines:
                    tax_line['parent_id'] = country_line_id
                    tax_line['level'] = 3
                    tax_parsed_id = report._parse_line_id(tax_line['id'])[-1]
                    tax_line['id'] = report._get_generic_line_id(
                        markup=tax_parsed_id[0],
                        model_name=tax_parsed_id[1],
                        value=tax_parsed_id[2],
                        parent_line_id=country_line['id']
                    )
                    rslt.append((0, tax_line))

        lines = super()._dynamic_lines_generator(report, options, all_column_groups_expression_totals, warnings=warnings)

        rslt = []
        tax_type_markups = {'sale', 'purchase'}
        tax_lines_by_country = defaultdict(lambda: [])
        last_tax_type_line = None
        for (dummy, line) in lines:
            markup, model, model_id = report._parse_line_id(line['id'])[-1]

            if markup in tax_type_markups:
                # Then it's a type_tax_use_section
                # If there were tax lines for the previous section, append them to rslt; the previous section is over
                append_country_and_taxes_lines(last_tax_type_line, rslt, tax_lines_by_country)
                last_tax_type_line = line

                # Start next section
                rslt.append((0, line))
                tax_lines_by_country = defaultdict(lambda: [])

            elif model == 'account.tax':
                # line is a tax line
                tax = self.env['account.tax'].browse(model_id)
                tax_oss_country = self.env['account.fiscal.position.tax'].search([('tax_dest_id', '=', tax.id)])\
                                                                         .mapped('position_id.country_id')

                if not tax_oss_country:
                    raise UserError(_("Tax %s is used on some OSS-tagged journal items in the period, but is not mapped by any fiscal position with a country set.", tax.display_name))
                elif len(tax_oss_country) > 1:
                    raise UserError(_("Inconsistent setup: OSS tax %s is mapped in fiscal positions from different countries.", tax.display_name))

                tax_lines_by_country[tax_oss_country].append(line)

        # Append the tax and country lines for the last section
        append_country_and_taxes_lines(last_tax_type_line, rslt, tax_lines_by_country)

        return rslt

    def _custom_options_initializer(self, report, options, previous_options):
        # Add OSS XML export if there is one available for the domestic country
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        if self._get_oss_xml_template(options):
            options.setdefault('buttons', []).append({
                'name': _('XML'),
                'sequence': 3,
                'action': 'export_file',
                'action_param': 'export_to_xml',
                'file_export_type': _('XML'),
                'branch_allowed': True,
            })
        options['forced_domain'] = [
            *options.get('forced_domain', []),
            *self._get_oss_custom_domain(),
        ]

    def export_to_xml(self, options):
        def get_period():
            """ Compute the values (Year, Quarter, Month) required for the 'Period' node.
            This node is used either at the XML root or inside the 'CorrectionsInfo' node.
            There are two possible cases for the latter:
                1. The total tax amount for the country is negative:
                --> We declare the corrections for the previous period.
                2. The country has at least one tax rate with a negative amount but its total is positive:
                --> We declare the corrections in the current period.
            """
            month = None
            quarter = None
            date_to = fields.Date.from_string(options['date']['date_to'])

            if options['date']['period_type'] == 'month':
                if previous_period:
                    date_to -= relativedelta(months=1)
                month = date_to.month
            elif options['date']['period_type'] == 'quarter':
                if previous_period:
                    date_to -= relativedelta(months=3)
                quarter = (int(date_to.month) - 1) // 3 + 1
            else:
                raise UserError(_('Choose a month or quarter to export the OSS report'))

            return date_to.year, quarter, month

        def get_line_data():
            year, quarter, month = get_period()
            return {
                'tax': tax,
                'net_amt': 0.0 if corrections_amount else line_net_amt,
                'tax_amt': 0.0 if corrections_amount else line_tax_amt,
                'corr_amt': corrections_amount,
                'corr_year': year,
                'corr_quarter': quarter,
                'corr_month': month,
                'currency': sender_company.currency_id,
                'supply_type': tax_scopes[tax.tax_scope].upper() if tax.tax_scope else 'GOODS',
                'rate_type': 'STANDARD' if tax.amount == eu_standard_rates[current_country.code] else 'REDUCED',
            }

        report = self.env['account.report'].browse(options['report_id'])
        oss_import_report = self.env.ref('l10n_eu_oss_reports.oss_imports_report')
        eu_countries = self.env.ref('base.europe').country_ids
        # prepare a dict of european standard tax rates {'AT': 20.0, 'BE': 21.0 ... }
        # sorted() is here needed to ensure the dict will contain the highest rate each time
        eu_standard_rates = {source_code: rate for source_code, rate, target_code in sorted(EU_TAX_MAP.keys())}
        tax_scopes = dict(self.env['account.tax'].fields_get()['tax_scope']['selection'])
        sender_company = report._get_sender_company_for_export(options)

        data = {}
        current_country = None
        corrections_amount = 0.0
        previous_period = False
        tax = None
        year, quarter, month = get_period()

        for line in filter(lambda x: x['columns'][1]['no_format'], report._get_lines(options)):
            model, model_id = report._get_model_info_from_id(line['id'])
            line_net_amt = line['columns'][0].get('no_format', 0.0)
            line_tax_amt = line['columns'][1].get('no_format', 0.0)

            if model == 'res.country':
                # If there are corrections (a.k.a. negative tax amounts) for the current country,
                # they are added at the end, right before the next country.
                # That is why the corrections amount is reset before moving on to the next country.
                if corrections_amount:
                    data[current_country].append(get_line_data())
                    corrections_amount = 0.0

                current_country = self.env['res.country'].browse(model_id)
                data[current_country] = []
                previous_period = line_tax_amt < 0.0

            elif model == 'account.tax':
                tax = self.env['account.tax'].browse(model_id)
                if line_tax_amt > 0.0:
                    data[current_country].append(get_line_data())
                else:
                    corrections_amount += line_tax_amt

        # If there are corrections for the last country,
        # they must be added here since we won't iterate through another country.
        if corrections_amount:
            data[current_country].append(get_line_data())

        values = {
            'VATNumber': sender_company.vat if sender_company.account_fiscal_country_id in eu_countries else None,
            'VoesNumber': sender_company.voes if sender_company.account_fiscal_country_id not in eu_countries else None,
            'IOSSNumber': sender_company.ioss if report == oss_import_report else None,
            'IntNumber': sender_company.intermediary_no if report == oss_import_report else None,
            'Year': year,
            'Quarter': quarter,
            'Month': month,
            'country_taxes': data,
            'creation_timestamp': fields.Datetime.context_timestamp(report, fields.Datetime.now()),
        }

        export_template_ref = self._get_oss_xml_template(options)
        rendered_content = self.env['ir.qweb']._render(export_template_ref, values)
        tree = objectify.fromstring(rendered_content)

        return {
            'file_name': report.get_default_report_filename(options, 'xml'),
            'file_content': etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding='utf-8'),
            'file_type': 'xml',
        }

    def _get_oss_xml_template(self, options):
        ''' Used to get the template ref for XML export
        Override this method to include additional templates for other countries
        Also serves as a check to verify if the options selected are conducive to an XML export
        '''
        country_code = self.env['account.report']._get_sender_company_for_export(options).account_fiscal_country_id.code
        if country_code == 'BE':
            return 'l10n_eu_oss_reports.eu_oss_generic_export_xml_be'
        if country_code == 'LU':
            return 'l10n_eu_oss_reports.eu_oss_generic_export_xml_lu'

        return None


class AccountTaxReportHandler(models.AbstractModel):
    _inherit = 'account.tax.report.handler'

    def _get_vat_closing_entry_additional_domain(self):
        # EXTENDS account_reports
        domain = super()._get_vat_closing_entry_additional_domain()
        domain += [
            ('tax_tag_ids', 'not in', self.env.ref('l10n_eu_oss.tag_oss').ids),
        ]
        return domain


class OSSTaxReportCustomHandlerSales(models.AbstractModel):
    _name = 'l10n_eu_oss.sales.tax.report.handler'
    _inherit = 'l10n_eu_oss.tax.report.handler'
    _description = 'OSS Tax Report Custom Handler (Sales)'

    def _get_oss_custom_domain(self):
        return [
            ('tax_tag_ids', 'in', self.env.ref('l10n_eu_oss.tag_oss').ids),
            ('tax_tag_ids', 'not in', self.env.ref('l10n_eu_oss.tag_eu_import').ids),
        ]


class OSSTaxReportCustomHandlerSalesImports(models.AbstractModel):
    _name = 'l10n_eu_oss.imports.tax.report.handler'
    _inherit = 'l10n_eu_oss.tax.report.handler'
    _description = 'OSS Tax Report Custom Handler (Imports)'

    def _get_oss_custom_domain(self):
        return [
            ('tax_tag_ids', 'in', self.env.ref('l10n_eu_oss.tag_oss').ids),
            ('tax_tag_ids', 'in', self.env.ref('l10n_eu_oss.tag_eu_import').ids),
        ]


class AccountReport(models.Model):
    _inherit = 'account.report'

    availability_condition = fields.Selection(selection_add=[('oss', "Using OSS")])

    def _is_available_for(self, options):
        # Overridden to support 'oss' availability condition
        if self.availability_condition == 'oss':
            oss_tag = self.env.ref('l10n_eu_oss.tag_oss')
            company_ids = self.get_report_company_ids(options)
            return bool(self.env['account.tax.repartition.line']\
                        .search([('tag_ids', 'in', oss_tag.ids), ('company_id', 'in', company_ids)], limit=1))
        else:
            return super()._is_available_for(options)
