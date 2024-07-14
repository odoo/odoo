# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from markupsafe import Markup

from odoo import _, fields, models
from odoo.exceptions import UserError
from .account_report import _raw_phonenumber, _get_xml_export_representative_node


class BelgianECSalesReportCustomHandler(models.AbstractModel):
    _name = 'l10n_be.ec.sales.report.handler'
    _inherit = 'account.ec.sales.report.handler'
    _description = 'Belgian EC Sales Report Custom Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        """
        This method is used to get the dynamic lines of the report and adds a comparative test linked to the tax report.
        """
        lines = super()._dynamic_lines_generator(report, options, all_column_groups_expression_totals, warnings=warnings)
        colname_to_idx = {col['expression_label']: idx for idx, col in enumerate(options['columns'])}

        if lines:
            total = lines[-1][-1]['columns'][colname_to_idx['balance']]['no_format']

            # This test requires the total, so needs to be checked after the lines are computed, but before the rendering
            # of the template. This is why we add it here even if it's not an option per se.
            if warnings is not None and not self.total_consistent_with_tax_report(options, total):
                warnings['l10n_be_reports.sales_report_warning_cross_check'] = {'alert_type': 'warning'}

        return lines

    def _caret_options_initializer(self):
        """
        Add custom caret option for the report to link to the partner and allow cleaner overrides.
        """
        return {
            'ec_sales': [
                {'name': _("View Partner"), 'action': 'caret_option_open_record_form'},
                {'name': _("Audit"), 'action': 'ec_sales_list_open_invoices', 'action_param': 'id'},
            ],
        }

    def _custom_options_initializer(self, report, options, previous_options=None):
        """
        Add the invoice lines search domain that is specific to the country.
        Typically, the taxes account.report.expression ids relative to the country for the triangular, sale of goods
        or services.
        :param dict options: Report options
        :return dict: The modified options dictionary
        """
        super()._init_core_custom_options(report, options, previous_options)
        ec_operation_category = options.get('sales_report_taxes', {'goods': tuple(), 'triangular': tuple(), 'services': tuple()})

        report_46L_expression = self.env.ref('l10n_be.tax_report_line_46L_tag')
        report_46T_expression = self.env.ref('l10n_be.tax_report_line_46T_tag')
        report_44_expression = self.env.ref('l10n_be.tax_report_line_44_tag')
        report_48s44_expression = self.env.ref('l10n_be.tax_report_line_48s44_tag')
        report_48s46T_expression = self.env.ref('l10n_be.tax_report_line_48s46T_tag')
        report_48s46L_expression = self.env.ref('l10n_be.tax_report_line_48s46L_tag')

        ec_operation_category['goods'] = tuple((report_46L_expression + report_48s46L_expression)._get_matching_tags().ids)
        ec_operation_category['triangular'] = tuple((report_46T_expression + report_48s46T_expression)._get_matching_tags().ids)
        ec_operation_category['services'] = tuple((report_44_expression + report_48s44_expression)._get_matching_tags().ids)

        # Change the names of the taxes to specific ones that are dependant to the tax type
        ec_operation_category['operation_category'] = {
            'goods': 'L (46L)',
            'triangular': 'T (46T)',
            'services': 'S (44)',
        }
        options.update({'sales_report_taxes': ec_operation_category})

        # Buttons
        options.setdefault('buttons', []).append({
            'name': _('XML'),
            'sequence': 30,
            'action': 'export_file',
            'action_param': 'export_to_xml_sales_report',
            'file_export_type': _('XML'),
        })

    def total_consistent_with_tax_report(self, options, total):
        """ Belgian EC Sales taxes report total must match
            Tax Report lines 44 + 46L + 46T - 48s44 - 48s46L - 48s46T.
        """
        vat_report = self.env.ref('l10n_be.tax_report_vat')
        tax_report_options = vat_report.get_options(options)

        expressions = self.env['account.report.expression']
        for expression_xmlid in ('l10n_be.tax_report_line_44_tag',
                                 'l10n_be.tax_report_line_46L_tag',
                                 'l10n_be.tax_report_line_46T_tag',
                                 'l10n_be.tax_report_line_48s44_tag',
                                 'l10n_be.tax_report_line_48s46L_tag',
                                 'l10n_be.tax_report_line_48s46T_tag'):
            expressions |= self.env.ref(expression_xmlid)

        tax_total = 0.0
        tax_total_grouped = vat_report._compute_expression_totals_for_each_column_group(expressions, tax_report_options)
        for expr_dict in tax_total_grouped.values():
            for expression, expr_total in expr_dict.items():
                if expression.formula[:2] == '48':
                    tax_total -= expr_total.get('value', 0.)
                else:
                    tax_total += expr_total.get('value', 0.)
        return self.env.company.currency_id.compare_amounts(tax_total, total) == 0

    def export_to_xml_sales_report(self, options):
        colname_to_idx = {col['expression_label']: idx for idx, col in enumerate(options.get('columns', []))}
        # Check
        company = self.env.company
        company_vat = company.partner_id.vat
        if not company_vat:
            raise UserError(_('No VAT number associated with your company.'))
        default_address = company.partner_id.address_get()
        address = default_address.get('invoice', company.partner_id)
        if not address.email:
            raise UserError(_('No email address associated with the company.'))
        if not address.phone:
            raise UserError(_('No phone associated with the company.'))

        # Generate xml
        post_code = street = city = country = data_clientinfo = ''
        company_vat = company_vat.replace(' ', '').upper()
        issued_by = company_vat[:2]

        seq_declarantnum = self.env['ir.sequence'].next_by_code('declarantnum')
        dnum = company_vat[2:] + seq_declarantnum[-4:]
        ads = None
        addr = company.partner_id.address_get(['invoice'])
        phone = email = city = post_code = street = country = company_country = ''
        report = self.env['account.report'].browse(options['report_id'])

        if addr.get('invoice', False):
            ads = self.env['res.partner'].browse([addr['invoice']])[0]

        if ads:
            if ads.phone:
                phone = _raw_phonenumber(ads.phone)
            elif address.phone:
                phone = _raw_phonenumber(address.phone)
            if ads.email:
                email = ads.email
            if ads.city:
                city = ads.city
            if ads.zip:
                post_code = ads.zip
            if ads.street:
                street = ads.street
            if ads.street2:
                street += ' ' + ads.street2

            company_country = ads.country_id.code if ads.country_id else company_vat[:2]

        options['no_format'] = True
        lines = report._get_lines(options)
        data_clientinfo = ''
        seq = 0
        for line in lines[:-1]:   # Remove total line
            country = line['columns'][colname_to_idx['country_code']].get('name', '')
            vat = line['columns'][colname_to_idx['vat_number']].get('name', '')
            amount = line['columns'][colname_to_idx['balance']]['no_format']
            if self.env.company.currency_id.is_zero(amount):
                continue
            if not vat:
                raise UserError(_('No vat number defined for %s.', line['name']))
            seq += 1
            client = {
                'vatnum': vat,
                'vat': (country + vat).replace(' ', '').upper(),
                'country': country,
                'amount': amount,
                'code': line['columns'][colname_to_idx['sales_type_code']]['name'][:1],
                'seq': seq,
            }
            data_clientinfo += Markup("""
        <ns2:IntraClient SequenceNumber="%(seq)s">
            <ns2:CompanyVATNumber issuedBy="%(country)s">%(vatnum)s</ns2:CompanyVATNumber>
            <ns2:Code>%(code)s</ns2:Code>
            <ns2:Amount>%(amount).2f</ns2:Amount>
        </ns2:IntraClient>""") % client

        xml_data = {
            'clientnbr': seq,
            'amountsum': lines[-1]['columns'][colname_to_idx['balance']]['no_format'] if lines else 0,
        }

        date_from = fields.Date.from_string(options['date'].get('date_from'))
        period_type = options['date'].get('period_type')
        month = date_from.month if period_type == 'month' else None
        quarter = (date_from.month - 1) // 3 + 1 if period_type == 'quarter' else None

        xml_data.update({
            'company_name': company.name,
            'company_vat': company_vat,
            'vatnum': company_vat[2:],
            'sender_date': str(time.strftime('%Y-%m-%d')),
            'street': street,
            'city': city,
            'post_code': post_code,
            'country': company_country,
            'email': email,
            'phone': _raw_phonenumber(phone),
            'year': date_from.year,
            'month': month,
            'quarter': quarter,
            'comments': '',
            'issued_by': issued_by,
            'dnum': dnum,
            'representative_node': _get_xml_export_representative_node(report),
        })

        data_head = Markup(f"""<?xml version="1.0" encoding="ISO-8859-1"?>
    <ns2:IntraConsignment xmlns="http://www.minfin.fgov.be/InputCommon" xmlns:ns2="http://www.minfin.fgov.be/IntraConsignment" IntraListingsNbr="1">
        %(representative_node)s
        <ns2:IntraListing SequenceNumber="1" ClientsNbr="%(clientnbr)s" DeclarantReference="%(dnum)s" AmountSum="%(amountsum).2f">
        <ns2:Declarant>
            <VATNumber>%(vatnum)s</VATNumber>
            <Name>%(company_name)s</Name>
            <Street>%(street)s</Street>
            <PostCode>%(post_code)s</PostCode>
            <City>%(city)s</City>
            <CountryCode>%(country)s</CountryCode>
            <EmailAddress>%(email)s</EmailAddress>
            <Phone>%(phone)s</Phone>
        </ns2:Declarant>
        <ns2:Period>
            {"<ns2:Month>%(month)s</ns2:Month>" if month else ""}
            {"<ns2:Quarter>%(quarter)s</ns2:Quarter>" if quarter else ""}
            <ns2:Year>%(year)s</ns2:Year>
        </ns2:Period>""") % xml_data

        data_rslt = data_head + data_clientinfo + Markup("""
        </ns2:IntraListing>
    </ns2:IntraConsignment>""")

        return {
            'file_name': report.get_default_report_filename(options, 'xml'),
            'file_content': data_rslt.encode('ISO-8859-1', 'ignore'),
            'file_type': 'xml',
        }

    def ec_sales_list_open_invoices(self, options, params=None):
        ec_category, _model, res_id = self.env['account.report']._parse_line_id(params['line_id'])[-1]

        domain = [
            ('move_id.move_type', 'in', self.env['account.move'].get_sale_types(include_receipts=True)),
            ('move_id.date', '>=', options['date']['date_from']),
            ('move_id.date', '<=', options['date']['date_to']),
            ('tax_tag_ids', 'in', options['sales_report_taxes'][ec_category]),
        ]

        return {
            'name': _('EC Sales List Audit'),
            'type': 'ir.actions.act_window',
            'views': [[self.env.ref('account.view_move_line_tree').id, 'list'], [False, 'form']],
            'res_model': 'account.move.line',
            'context': {
                'search_default_partner_id': res_id,
                'search_default_group_by_partner': 1,
                'expand': 1,
            },
            'domain': domain,
        }
