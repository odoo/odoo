# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from lxml import etree

from odoo import fields, models, release, _
from odoo.exceptions import UserError
from odoo.tools import date_utils
from odoo.tools.misc import get_lang

_logger = logging.getLogger(__name__)


class AccountGenericTaxReport(models.AbstractModel):
    _name = 'l10n_no.tax.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = "Norvegian Tax Report Custom Handler"

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        options.setdefault('buttons', []).append({
            'name': _('XML'),
            'sequence': 3,
            'action': 'export_file',
            'action_param': 'print_norwegian_report_xml',
            'file_export_type': _('XML'),
        })

    def _l10n_no_set_time_interval(self, options):
        """Set the correct time interval based on the dates of the report.

        A time interval is a string in Norwegian that represents the starting and ending months of the report
        (example: "januar-februar").

        If the report is for only one month or for the whole year, the time interval is different
        (example: "januar" for a single month or "aarlig" for a full year).

        :rtype: dict
        :returns: a dictionary with values useful to set a time interval
        """
        date_from = fields.Date.to_date(options['date']['date_from'])
        date_to = fields.Date.to_date(options['date']['date_to'])

        if date_from.day != 1 or date_to.day != date_utils.end_of(date_to, 'month').day:
            raise UserError(_("The chosen date interval is invalid, it should be from the start of one month to the end of the other month"))

        month_from = date_from.month
        month_to = date_to.month
        year_from = date_from.year
        year_to = date_to.year

        number_of_months = (year_to - year_from) * 12 + (month_to - month_from) + 1  # +1, it's the end of the month

        if number_of_months not in (1, 2, 3, 6, 12) or month_to % number_of_months != 0:
            raise UserError(_("The chosen dates do not correspond to a valid time interval for the tax return XML"))

        norwegian_months = {
            0: 'aarlig',
            1: 'januar',
            2: 'februar',
            3: 'mars',
            4: 'april',
            5: 'mai',
            6: 'juni',
            7: 'juli',
            8: 'august',
            9: 'september',
            10: 'oktober',
            11: 'november',
            12: 'desember',
        }
        if number_of_months in (1, 12):
            months_str_terms = [norwegian_months[month_to % 12]]
        else:
            months_str_terms = [norwegian_months[month_from], norwegian_months[month_to]]

        time_period = '-'.join(months_str_terms)
        return {
            'date_from': options['date']['date_from'],
            'date_to': options['date']['date_to'],
            'time_period': time_period,
            'year': year_from,
            'number_of_months': number_of_months,
        }

    def _l10n_no_query_taxes(self, report, options):
        """Fetch taxes to fill the xml file.

        Taxes can either be input or output taxes. Input taxes have a negative tax amount while output taxes have a
        positive one. Inside the xml file, input taxes don't need to display a base amount, only a tax amount.

        Most (standard) taxes are grouped by their codes (norwegian tax codes), in order to have for each tax the total
        base amount, as well as the total tax amount.

        :rtype: dict
        :returns: a dictionary with:
          (1) the total amount to be paid to the authorities
          (2) a list of taxes (dictionaries) to be displayed in the XML
        """

        tables, where_clause, where_params = report._query_get(options, 'strict_range')
        tax_details_query, tax_details_params = self.env['account.move.line']._get_query_tax_details(tables, where_clause, where_params)

        # The following tax details query will group taxes with their tax repartition lines in order to have one result
        # per standard tax and two results per deductible taxes.
        if self.pool['account.tax'].name.translate: # Will be true if l10n_multilang is installed
            lang = self.env.user.lang or get_lang(self.env).code
            acc_tag_name = f"COALESCE(tag.name->>'{lang}', tag.name->>'en_US')"
            tax_name = f"COALESCE(tax.name->>'{lang}', tax.name->>'en_US')"
        else:
            acc_tag_name = 'tag.name'
            tax_name = 'tax.name'

        self._cr.execute(f'''
            SELECT
                /* Take the opposite to reflect amounts due to and owed by the tax authorities */
                SUM(-tdr.tax_amount) AS tax_amount,
                SUM(-tdr.base_amount) AS base_amount,
                tax.amount AS rate,
                {tax_name} AS name,
                SUBSTRING(report_line.code, '[0-9]+') AS tax_code
            FROM ({tax_details_query}) AS tdr
            JOIN account_tax_repartition_line trl ON trl.id = tdr.tax_repartition_line_id
            JOIN account_tax tax ON tax.id = tdr.tax_id
            JOIN account_tax src_tax ON
                src_tax.id = COALESCE(tdr.group_tax_id, tdr.tax_id)
                AND src_tax.type_tax_use IN ('sale', 'purchase')
            JOIN account_account account ON account.id = tdr.base_account_id
            JOIN account_account_tag_account_tax_repartition_line_rel repartition_rel ON repartition_rel.account_tax_repartition_line_id = trl.id
            JOIN account_account_tag tag ON
                tag.id = repartition_rel.account_account_tag_id
                AND tag.applicability = 'taxes'
                AND tag.country_id = %s
            JOIN account_report_expression expression ON expression.engine = 'tax_tags' AND expression.formula = SUBSTRING({acc_tag_name} from 2)
            JOIN account_report_line report_line ON expression.report_line_id = report_line.id
            JOIN res_country tax_country ON tax_country.id = tax.country_id
            WHERE tdr.tax_exigible
            GROUP BY tdr.tax_repartition_line_id, tax.id, report_line.code
        ''', [*tax_details_params, self.env.ref('base.no').id])

        tax_details_list = self._cr.dictfetchall()
        tax_total = sum(row['tax_amount'] for row in tax_details_list)
        return {
            'tax_total': tax_total,
            'tax_details_list': tax_details_list,
        }

    def print_norwegian_report_xml(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        sender_company = report._get_sender_company_for_export(options)
        if not sender_company.l10n_no_bronnoysund_number:
            raise UserError(_("No number for the Register of Legal Entities, please set one up for company %s", sender_company.name))

        # Number used for bill payment in Norway to identify the customer and the invoice, abbreviated KID
        # (KID = kundeidentifikasjon)
        if not sender_company.vat:
            raise UserError(_("No KID number, please set one up for company %s", sender_company.name))

        time_interval_dict = self._l10n_no_set_time_interval(options)
        tax_details_dict = self._l10n_no_query_taxes(report, options)

        data = {
            'xmlns': 'no:skatteetaten:fastsetting:avgift:mva:skattemeldingformerverdiavgift:v1.0',
            'submission_ref': 1,  # Always 1 - no online submission (yet)
            'odoo_version': release.version,
            'company_kid': sender_company.vat,
            'company_bronnoysund_number': sender_company.l10n_no_bronnoysund_number,
            'company_name': sender_company.name,
            'category': "alminnelig",
            'note': f"Mva-melding for {sender_company.name}",
            'sender_company': sender_company,
            **time_interval_dict,
            **tax_details_dict,
        }
        xml_content = self.env['ir.qweb']._render('l10n_no_reports.no_evat_template', values=data)
        tree = etree.fromstring(xml_content, parser=etree.XMLParser(remove_blank_text=True))
        formatted_xml = etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding='UTF-8')

        return {
            'file_name': report.get_default_report_filename(options, 'xml'),
            'file_content': formatted_xml,
            'file_type': 'xml',
        }
