# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.tools import groupby, SQL
from odoo.exceptions import UserError
from markupsafe import Markup
from .account_report import _raw_phonenumber, _get_xml_export_representative_node

from stdnum.eu.vat import compact
from stdnum.be.vat import compact as vat_be_compact
from stdnum.exceptions import ValidationError


class PartnerVATListingCustomHandler(models.AbstractModel):
    _name = 'l10n_be.partner.vat.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Partner VAT Listing Custom Handler'

    def _caret_options_initializer(self):
        return {
            'res.partner': [
                {'name': _("View Partner"), 'action': 'caret_option_open_record_form'},
                {'name': _("Audit"), 'action': 'partner_vat_listing_open_invoices'},
            ],
            'account.account': [
                {'name': _("Audit"), 'action': 'partner_vat_listing_open_invoices'},
            ],
        }

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        operations_tags_expr = [
            'l10n_be.tax_report_line_00_tag', 'l10n_be.tax_report_line_01_tag', 'l10n_be.tax_report_line_02_tag',
            'l10n_be.tax_report_line_03_tag', 'l10n_be.tax_report_line_45_tag', 'l10n_be.tax_report_line_49_tag',
        ]

        operation_expressions = self.env['account.report.expression']

        for xmlid in operations_tags_expr:
            operation_expressions += self.env.ref(xmlid)

        options['partner_vat_listing_operations_tag_ids'] = operation_expressions._get_matching_tags().ids

        taxes_tags_expr = ['l10n_be.tax_report_line_54_tag', 'l10n_be.tax_report_line_64_tag']
        tax_expressions = self.env['account.report.expression']

        for xmlid in taxes_tags_expr:
            tax_expressions += self.env.ref(xmlid)

        options['partner_vat_listing_taxes_tag_ids'] = tax_expressions._get_matching_tags().ids

        options['buttons'] += [{
            'name': _('XML'),
            'sequence': 30,
            'action': 'export_file',
            'action_param': 'partner_vat_listing_export_to_xml',
            'file_export_type': _('XML')
        }]

        self._enable_export_buttons_for_common_vat_groups_in_branches(options)

    def _custom_line_postprocessor(self, report, options, lines, warnings=None):
        if warnings is not None:
            warning_partners = self._get_warning_partners(report, options)
            if warning_partners:
                warnings['l10n_be_reports.partner_vat_listing_missing_partners_warning'] = {
                    'alert_type': 'warning',
                    'count': len(warning_partners),
                    'ids': warning_partners,
                }

        return lines

    def action_warning_partners(self, options, params):
        view_id = (
                self.env.ref('l10n_be_reports.res_partner_vat_listing_warning_view_tree', raise_if_not_found=False) or
                self.env.ref('base.view_partner_tree')  # In case the DB was not updated.
        ).id
        return {
            'name': _('Missing partners'),
            'res_model': 'res.partner',
            'views': [(view_id, 'tree')],
            'domain': [('id', 'in', params['ids'])],
            'type': 'ir.actions.act_window',
        }

    def _get_excluded_taxes(self):
        tag_49_ids = self.env.ref('l10n_be.tax_report_line_49').expression_ids._get_matching_tags().ids
        trl_49 = self.env['account.tax.repartition.line'].search([('tag_ids', 'in', tag_49_ids), ('document_type', '=', 'refund')])
        tag_47_ids = self.env.ref('l10n_be.tax_report_line_47').expression_ids._get_matching_tags().ids
        trl_47 = self.env['account.tax.repartition.line'].search([('tag_ids', 'in', tag_47_ids), ('document_type', '=', 'invoice')])
        return trl_47.tax_id & trl_49.tax_id

    def _get_query_fun_params(self, report, options, remove_forced_domain=False):
        # Remove the forced_domain possibly used in the options to force the value of the groupby being unfolded/horizontal group. Indeed, we want
        # the turnover/refund check to apply globally.
        new_options = {**options, 'forced_domain': []} if remove_forced_domain else options
        excluded_tax_ids = self._get_excluded_taxes().ids

        tables, where_clause, where_params = report._query_get(new_options, 'strict_range')
        return {
            'options': new_options,
            'excluded_tax_ids': excluded_tax_ids,
            'tables': tables,
            'where_clause': where_clause,
            'where_params': where_params,
        }

    def _report_custom_engine_partner_vat_listing(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        def build_result_dict(query_res_lines, partners_vat_map):
            vat_number = None
            if current_groupby == 'partner_id':
                partner_vat = partners_vat_map[query_res_lines[0]['grouping_key']]
                try:
                    vat_number = compact(partner_vat)
                except ValidationError:
                    vat_number = partner_vat

            rslt = {
                'vat_number': vat_number,
                'turnover': 0,
                'vat_amount': 0,
                'has_sublines': False,
            }

            for line in query_res_lines:
                rslt['turnover'] += line['turnover']
                rslt['vat_amount'] += line['vat_amount']

            return rslt

        report = self.env['account.report'].browse(options['report_id'])
        report._check_groupby_fields((next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))

        partners_vat_map = self._get_accepted_partners_vat_map(report, options)

        partner_ids = [partner_id for partner_id in partners_vat_map]

        if not partner_ids:
            return [] if current_groupby else {'vat_number': None, 'turnover': 0, 'vat_amount': 0, 'has_sublines': False}

        tail_query, tail_params = report._get_engine_query_tail(offset, limit)

        if current_groupby == 'partner_id':
            grouping_key_param = 'res_partner.id'
        elif current_groupby:
            grouping_key_param = f'account_move_line.{current_groupby}'
        else:
            grouping_key_param = 'NULL'

        query_fun_params = self._get_query_fun_params(report, options) | {'partner_ids': partner_ids}

        turnover_from, turnover_where, turnover_where_params = self._get_turnover_query(**query_fun_params)
        refund_base_from, refund_base_where, refund_base_where_params = self._get_refund_base_query(**query_fun_params)
        vat_amounts_from, vat_amounts_where, vat_amounts_where_params = self._get_vat_amounts_query(**query_fun_params)

        query = f"""
        SELECT subquery.grouping_key AS grouping_key,
               SUM(subquery.turnover) AS turnover,
               SUM(subquery.refund_base) AS refund_base,
               SUM(subquery.vat_amount) AS vat_amount,
               SUM(subquery.refund_vat_amount) AS refund_vat_amount
          FROM (
                SELECT
                    {grouping_key_param} AS grouping_key,
                    COALESCE(SUM(account_move_line.credit - account_move_line.debit), 0) AS turnover,
                    0 AS refund_base,
                    0 AS vat_amount,
                    0 AS refund_vat_amount
                FROM {turnover_from}
                WHERE {turnover_where}
                {f'GROUP BY {grouping_key_param}' if current_groupby else ''}

                UNION ALL

                SELECT
                    {grouping_key_param} AS grouping_key,
                    0 AS turnover,
                    COALESCE(SUM(account_move_line.debit - account_move_line.credit), 0) AS refund_base,
                    0 AS vat_amount,
                    0 AS refund_vat_amount
                FROM {refund_base_from}
                WHERE {refund_base_where}
                {f'GROUP BY {grouping_key_param}' if current_groupby else ''}

                UNION ALL

                SELECT
                    {grouping_key_param} AS grouping_key,
                    0 AS turnover,
                    0 AS refund_base,
                    COALESCE(SUM(account_move_line.credit - account_move_line.debit), 0) AS vat_amount,
                    COALESCE(SUM(account_move_line.debit), 0) AS refund_vat_amount
                FROM {vat_amounts_from}
                WHERE {vat_amounts_where}
                {f'GROUP BY {grouping_key_param}' if current_groupby else ''}
          ) AS subquery
          GROUP BY subquery.grouping_key
          ORDER BY subquery.grouping_key
          {tail_query}
      """

        self._cr.execute(query, turnover_where_params + refund_base_where_params + vat_amounts_where_params + tail_params)
        all_query_res = self._cr.dictfetchall()

        if not current_groupby:
            return build_result_dict(all_query_res, partners_vat_map)
        else:
            rslt = []
            all_res_per_grouping_key = {}

            for query_res in all_query_res:
                grouping_key = query_res.get('grouping_key')
                all_res_per_grouping_key.setdefault(grouping_key, []).append(query_res)

            for grouping_key, query_res_lines in all_res_per_grouping_key.items():
                rslt.append((grouping_key, build_result_dict(query_res_lines, partners_vat_map)))

            return rslt

    def _get_accepted_partners_vat_map(self, report, options):
        query_fun_params = self._get_query_fun_params(report, options, remove_forced_domain=True)

        turnover_from, turnover_where, turnover_where_params = self._get_turnover_query(**query_fun_params)
        refund_base_from, refund_base_where, refund_base_where_params = self._get_refund_base_query(**query_fun_params)
        vat_amounts_from, vat_amounts_where, vat_amounts_where_params = self._get_vat_amounts_query(**query_fun_params)

        query = f"""
            SELECT res_partner.id, res_partner.vat
            FROM {turnover_from}
            WHERE {turnover_where}
            AND res_partner.vat ILIKE %s
            GROUP BY res_partner.id, res_partner.vat
            HAVING SUM(account_move_line.credit - account_move_line.debit) > 250

            UNION

            SELECT res_partner.id, res_partner.vat
            FROM {refund_base_from}
            WHERE {refund_base_where}
            AND res_partner.vat ILIKE %s
            GROUP BY res_partner.id, res_partner.vat
            HAVING SUM(account_move_line.balance) > 0

            UNION

            SELECT res_partner.id, res_partner.vat
            FROM {vat_amounts_from}
            WHERE {vat_amounts_where}
            AND res_partner.vat ILIKE %s
            GROUP BY res_partner.id, res_partner.vat
            HAVING SUM(account_move_line.debit) > 0
        """

        be_format = r'BE%'
        self._cr.execute(query, [*turnover_where_params, be_format, *refund_base_where_params, be_format, *vat_amounts_where_params, be_format])
        return dict(self._cr.fetchall())

    def _get_warning_partners(self, report, options):
        """
        Returns a list of partner IDs that should potentially have been included in the report. Those are partners
        with a turnover of more than 250 or at least one credit note and one of the following:
        - No country and tax ID.
        - Country = BE and no tax ID or tax ID not starting with BE.
        - No country specified and tax ID starting with BE.
        """
        query_fun_params = self._get_query_fun_params(report, options, remove_forced_domain=True)

        turnover_from, turnover_where, turnover_where_params = self._get_turnover_query(**query_fun_params)
        refund_base_from, refund_base_where, refund_base_where_params = self._get_refund_base_query(**query_fun_params)
        vat_amounts_from, vat_amounts_where, vat_amounts_where_params = self._get_vat_amounts_query(**query_fun_params)

        query = f"""
            SELECT id
            FROM (
                SELECT res_partner.id as id, res_partner.country_id as country_id, res_partner.vat as vat
                FROM {turnover_from}
                WHERE {turnover_where}
                GROUP BY res_partner.id
                HAVING SUM(account_move_line.credit - account_move_line.debit) > 250

                UNION

                SELECT res_partner.id as id, res_partner.country_id as country_id, res_partner.vat as vat
                FROM {refund_base_from}
                WHERE {refund_base_where}
                GROUP BY res_partner.id
                HAVING SUM(account_move_line.balance) > 0

                UNION

                SELECT res_partner.id as id, res_partner.country_id as country_id, res_partner.vat as vat
                FROM {vat_amounts_from}
                WHERE {vat_amounts_where}
                GROUP BY res_partner.id
                HAVING SUM(account_move_line.debit) > 0
            ) as partner_ids
            WHERE
                (country_id IS NULL AND vat IS NULL)
                OR (country_id IS NULL AND vat NOT ILIKE %s)
                OR (country_id = %s AND vat IS NULL)
                OR (country_id = %s AND vat NOT ILIKE %s)
        """

        be_format = r'BE%'
        be_country_id = self.env.ref('base.be').id
        self._cr.execute(SQL(query, *turnover_where_params, *refund_base_where_params, *vat_amounts_where_params, be_format, be_country_id, be_country_id, be_format))
        return [r[0] for r in self._cr.fetchall()]

    def _get_turnover_query(self, options, excluded_tax_ids, tables, where_clause, where_params, partner_ids=None):
        turnover_from = f"""
            {tables}
            JOIN account_account_tag_account_move_line_rel aml_tag
                ON account_move_line.id = aml_tag.account_move_line_id
            LEFT JOIN account_move
                ON account_move_line.move_id = account_move.id
            LEFT JOIN res_partner
                ON COALESCE(account_move_line.partner_id, account_move.partner_id) = res_partner.id
        """

        turnover_where = f"""
            {where_clause}
            AND aml_tag.account_account_tag_id IN %s
            AND (
                (account_move.move_type = 'entry' AND account_move_line.credit > 0)
                OR account_move.move_type IN ('out_refund', 'out_invoice')
            )
            AND account_move.state = 'posted'
            {'AND res_partner.id IN %s' if partner_ids else ''}
            {'''AND NOT EXISTS (
                SELECT 1
                FROM account_move_line_account_tax_rel amlatr
                WHERE account_move_line.id = amlatr.account_move_line_id
                AND amlatr.account_tax_id IN %s
            )''' if excluded_tax_ids else ''}
        """

        turnover_where_params = [*where_params, tuple(options['partner_vat_listing_operations_tag_ids'])]
        if partner_ids:
            turnover_where_params.append(tuple(partner_ids))
        if excluded_tax_ids:
            turnover_where_params.append(tuple(excluded_tax_ids))

        return turnover_from, turnover_where, turnover_where_params

    def _get_refund_base_query(self, options, excluded_tax_ids, tables, where_clause, where_params, partner_ids=None):
        refund_base_from = f"""
            {tables}
            JOIN account_account_tag_account_move_line_rel aml_tag
                ON account_move_line.id = aml_tag.account_move_line_id
            LEFT JOIN account_move
                ON account_move_line.move_id = account_move.id
            JOIN res_partner
                ON COALESCE(account_move_line.partner_id, account_move.partner_id) = res_partner.id
        """

        refund_base_where = f"""
            {where_clause}
            AND aml_tag.account_account_tag_id IN %s
            AND (
                (account_move.move_type = 'entry' AND account_move_line.credit > 0)
                OR account_move.move_type = 'out_refund'
            )
            AND account_move.state = 'posted'
            {'AND res_partner.id IN %s' if partner_ids else ''}
            {'''AND NOT EXISTS (
                SELECT 1
                FROM account_move_line_account_tax_rel amlatr
                WHERE account_move_line.id = amlatr.account_move_line_id
                AND amlatr.account_tax_id IN %s
            )''' if excluded_tax_ids else ''}
        """

        refund_base_where_params = [*where_params, tuple(options['partner_vat_listing_operations_tag_ids'])]
        if partner_ids:
            refund_base_where_params.append(tuple(partner_ids))
        if excluded_tax_ids:
            refund_base_where_params.append(tuple(excluded_tax_ids))

        return refund_base_from, refund_base_where, refund_base_where_params

    def _get_vat_amounts_query(self, options, excluded_tax_ids, tables, where_clause, where_params, partner_ids=None):
        vat_amounts_from = f"""
           {tables}
           JOIN account_account_tag_account_move_line_rel aml_tag2
               ON account_move_line.id = aml_tag2.account_move_line_id
           LEFT JOIN account_move
               ON account_move_line.move_id = account_move.id
           JOIN res_partner
               ON COALESCE(account_move_line.partner_id, account_move.partner_id) = res_partner.id
        """

        vat_amounts_where = f"""
           {where_clause}
           AND aml_tag2.account_account_tag_id IN %s
           AND (
               (account_move.move_type = 'entry' AND account_move_line.credit > 0)
               OR account_move.move_type IN ('out_refund', 'out_invoice')
           )
           AND account_move.state = 'posted'
           {'AND res_partner.id IN %s' if partner_ids else ''}
           {'AND account_move_line.tax_line_id NOT IN %s' if excluded_tax_ids else ''}
        """

        vat_amounts_where_params = [*where_params, tuple(options['partner_vat_listing_taxes_tag_ids'])]
        if partner_ids:
            vat_amounts_where_params.append(tuple(partner_ids))
        if excluded_tax_ids:
            vat_amounts_where_params.append(tuple(excluded_tax_ids))

        return vat_amounts_from, vat_amounts_where, vat_amounts_where_params

    def partner_vat_listing_open_invoices(self, options, params=None):
        report = self.env['account.report'].browse(options['report_id'])

        line_domain = report._get_audit_line_domain(
            options,
            self.env['account.report.expression'], # Arbitrary, just used to get the date_scope
            {'calling_line_dict_id': params['line_id']}
        )

        domain = [
            *line_domain,
            ('move_id.move_type', 'in', self.env['account.move'].get_sale_types(include_receipts=True)),
            ('move_id.partner_id.vat', '=ilike', 'BE%'),
            ('tax_tag_ids', 'in', options['partner_vat_listing_operations_tag_ids'] + options['partner_vat_listing_taxes_tag_ids']),
        ]

        return {
            'name': _('VAT Listing Audit'),
            'type': 'ir.actions.act_window',
            'views': [[self.env.ref('account.view_move_line_tree').id, 'list'], [False, 'form']],
            'res_model': 'account.move.line',
            'context': {'expand': 1, 'search_default_group_by_partner': 1},
            'domain': domain,
        }

    def partner_vat_listing_export_to_xml(self, options):
        # Precheck
        company = self.env.company
        company_vat = company.partner_id.vat
        report = self.env['account.report'].browse(options['report_id'])

        if not company_vat:
            raise UserError(_('No VAT number associated with your company.'))

        default_address = company.partner_id.address_get()
        address = default_address.get('invoice', company.partner_id)

        if not address.email:
            raise UserError(_('No email address associated with the company.'))

        if not address.phone:
            raise UserError(_('No phone associated with the company.'))

        # Write xml
        seq_declarantnum = self.env['ir.sequence'].next_by_code('declarantnum')
        company_bce_number = vat_be_compact(company_vat)
        dnum = f'{company_bce_number}{seq_declarantnum[-4:]}'
        street = city = country = ''
        addr = company.partner_id.address_get(['invoice'])

        if addr.get('invoice', False):
            addr_partner = self.env['res.partner'].browse([addr['invoice']])
            phone = addr_partner.phone and _raw_phonenumber(addr_partner.phone) or address.phone and _raw_phonenumber(address.phone)
            email = addr_partner.email or ''
            city = addr_partner.city or ''
            zip_code = addr_partner.zip or ''

            if not city:
                city = ''
            if addr_partner.street:
                street = addr_partner.street
            if addr_partner.street2:
                street += ' ' + addr_partner.street2
            if addr_partner.country_id:
                country = addr_partner.country_id.code

        # Turnover and Farmer tags are not included
        options['date']['date_from'] = options['date']['date_from'][0:4] + '-01-01'
        options['date']['date_to'] = options['date']['date_to'][0:4] + '-12-31'
        lines = report._get_lines(options)
        partner_lines = filter(lambda line: report._get_model_info_from_id(line['id'])[0] == 'res.partner', lines)

        data_client_info = ''
        seq = 0
        sum_turnover = 0.00
        sum_tax = 0.00

        for vat_number, values in groupby(partner_lines, key=lambda line: line['columns'][0]['name']):
            turnover = 0.0
            vat_amount = 0.0

            for value in list(values):

                for column in value['columns']:
                    col_expr_label = column['expression_label']

                    if col_expr_label == 'turnover':
                        turnover += column['no_format'] or 0.0
                    elif col_expr_label == 'vat_amount':
                        vat_amount += column['no_format'] or 0.0

            seq += 1
            sum_turnover += turnover
            sum_tax += vat_amount
            amount_data = {
                'seq': str(seq),
                'only_vat': vat_be_compact(vat_number),
                'turnover': turnover,
                'vat_amount': vat_amount,
            }
            data_client_info += Markup("""
        <ns2:Client SequenceNumber="%(seq)s">
            <ns2:CompanyVATNumber issuedBy="BE">%(only_vat)s</ns2:CompanyVATNumber>
            <ns2:TurnOver>%(turnover).2f</ns2:TurnOver>
            <ns2:VATAmount>%(vat_amount).2f</ns2:VATAmount>
        </ns2:Client>""") % amount_data

        annual_listing_data = {
            'comp_name': company.name,
            'street': street,
            'zip_code': zip_code,
            'city': city,
            'country': country,
            'email': email,
            'phone': phone,
            'SenderId': company_bce_number,
            'period': options['date'].get('date_from')[0:4],
            'comments': '',
            'seq': str(seq),
            'dnum': dnum,
            'sum_turnover': sum_turnover,
            'sum_tax': sum_tax,
            'representative_node': _get_xml_export_representative_node(report),
        }

        data_begin = Markup("""<?xml version="1.0" encoding="ISO-8859-1"?>
<ns2:ClientListingConsignment xmlns="http://www.minfin.fgov.be/InputCommon" xmlns:ns2="http://www.minfin.fgov.be/ClientListingConsignment" ClientListingsNbr="1">
    %(representative_node)s
    <ns2:ClientListing SequenceNumber="1" ClientsNbr="%(seq)s" DeclarantReference="%(dnum)s"
        TurnOverSum="%(sum_turnover).2f" VATAmountSum="%(sum_tax).2f">
        <ns2:Declarant>
            <VATNumber>%(SenderId)s</VATNumber>
            <Name>%(comp_name)s</Name>
            <Street>%(street)s</Street>
            <PostCode>%(zip_code)s</PostCode>
            <City>%(city)s</City>
            <CountryCode>%(country)s</CountryCode>
            <EmailAddress>%(email)s</EmailAddress>
            <Phone>%(phone)s</Phone>
        </ns2:Declarant>
        <ns2:Period>%(period)s</ns2:Period>""") % annual_listing_data

        data_end = Markup("""
        <ns2:Comment>%(comments)s</ns2:Comment>
    </ns2:ClientListing>
</ns2:ClientListingConsignment>""") % annual_listing_data

        return {
            'file_name': report.get_default_report_filename(options, 'xml'),
            'file_content': (data_begin + data_client_info + data_end).encode('ISO-8859-1', 'ignore'),
            'file_type': 'xml',
        }
