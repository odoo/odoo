import json

from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import SQL


class L10nPlJPKFAReportHandler(models.AbstractModel):

    _name = 'l10n.pl.reports.jpk.fa.report.handler'
    _inherit = ['account.partner.ledger.report.handler']
    _description = "Polish JPK FA Report Handler"

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        # Remove multi-currency columns if needed
        if self.env.user.has_group('base.group_multi_currency'):
            options['multi_currency'] = True
        else:
            options['columns'] = [col for col in options['columns'] if col['expression_label'] != 'amount_in_currency']

        options.setdefault('buttons', []).append({
            'name': 'XML',
            'sequence': 5,
            'action': 'print_jpk_fa_xml',
            'file_export_type': 'XML',
            'branch_allowed': True,
            'always_show': True,
        })

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        invoice_lines, totals = self._build_invoice_lines(report, options)

        # Inject sequence on dynamic lines
        lines = [(0, line) for line in invoice_lines]

        # Report total line.
        lines.append((0, self._get_report_line_total(report, options, totals)))

        return lines

    @api.model
    def action_open_partner(self, options, params):
        _, move_id = self.env['account.report']._get_model_info_from_id(params['id'])
        partner_id = self.env['account.move'].browse(move_id).partner_id
        return partner_id._get_records_action()

    def open_journal_items(self, options, params):
        report = self.env['account.report'].browse(options['report_id'])

        _, record_id = report._get_model_info_from_id(params.get('line_id'))
        move_line_ids = self.env['account.move'].browse(record_id).invoice_line_ids

        return move_line_ids._get_records_action(name=self.env._("Journal Items"))

    # ------------------------------------------------------
    # Report view : Invoices
    # ------------------------------------------------------

    def _build_invoice_lines(self, report, options, level_shift=0):
        """ Build invoice lines and the total line for the report view """
        lines = []

        invoices_results = self._query_invoice_lines(options)
        totals = defaultdict(float)
        currency_ids = {inv['currency_id'] for inv in invoices_results if inv.get('currency_id')}
        currencies = self.env['res.currency'].browse(list(currency_ids)).grouped('id')

        for invoice in invoices_results:
            totals['amount_total'] += invoice['amount_total']
            totals['amount_net'] += invoice['amount_net']
            totals['amount_tax'] += invoice['amount_tax']
            lines.append(self._get_report_line(report, options, invoice['id'], invoice, currencies, level_shift=level_shift))

        return lines, totals

    def _query_invoice_lines(self, options):
        """ Query executed when opening the report
            We only fetch the invoices that are not already accepted by KSeF
        """
        move_query = self.env['account.move']._where_calc([
            *self.env['account.move']._check_company_domain(self.env.companies),
            ('move_type', 'in', self.env['account.move'].get_sale_types()),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', options['date']['date_from']),
            ('invoice_date', '<=', options['date']['date_to']),
            ('l10n_pl_edi_status', 'not in', ('accepted',))
        ])

        query = SQL(
            """
            SELECT account_move.id,
                   account_move.name,
                   account_move.invoice_date,
                   account_move.invoice_date_due,
                   account_move.currency_id,
                   account_move.amount_untaxed_signed  AS amount_net,
                   account_move.amount_tax_signed      AS amount_tax,
                   account_move.amount_total_signed    AS amount_total,
                   account_move.amount_total           AS amount_in_currency,
                   partner.name                        AS partner_name
              FROM account_move
         LEFT JOIN res_partner partner ON partner.id = account_move.partner_id
             WHERE %(search_condition)s
          ORDER BY invoice_date ASC, id ASC
            """,
            search_condition=move_query.where_clause,
        )
        self.env.cr.execute(query)
        return self.env.cr.dictfetchall()

    def _get_report_line(self, report, options, invoice_id, invoice_values, currencies, level_shift=0):
        column_values = []
        for column in options['columns']:
            col_expr_label = column['expression_label']
            value = invoice_values.get(col_expr_label, '')
            currency = False

            if col_expr_label == 'amount_in_currency':
                currency = currencies[invoice_values['currency_id']]
                if currency == self.env.company.currency_id:
                    value = ''

            column_values.append(report._build_column_dict(value, column, options=options, currency=currency))

        line_id = report._get_generic_line_id('account.move', invoice_id)

        return {
            'id': line_id,
            'name': invoice_values['name'],
            'columns': column_values,
            'level': 1 + level_shift,
            'unfoldable': True,
            'unfolded': line_id in options['unfolded_lines'] or options['unfold_all'],
            'expand_function': '_report_expand_unfoldable_line_invoice',
        }

    def _get_report_line_total(self, report, options, totals):
        column_values = []
        for column in options['columns']:
            col_value = totals.get(column['expression_label'])
            column_values.append(report._build_column_dict(col_value, column, options=options))

        return {
            'id': report._get_generic_line_id(None, None, markup='total'),
            'name': self.env._('Total'),
            'level': 1,
            'columns': column_values,
        }

    # ------------------------------------------------------
    # Report view : Invoice lines
    # ------------------------------------------------------

    def _report_expand_unfoldable_line_invoice(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        report = self.env['account.report'].browse(options['report_id'])
        _, _, record_id = report._parse_line_id(line_dict_id)[-1]

        aml_results = self._get_aml_values(options, report, record_id)

        return self._get_invoice_aml_report_lines(report, options, line_dict_id, aml_results, progress, level_shift=1)

    def _get_aml_values(self, options, report, invoice_id):
        """ Query executed when unfolding a line of the report """
        query = report._get_report_query(options, 'strict_range')

        query_to_execute = SQL(
            """
                 SELECT account_move_line.id,
                        account_move_line.name,
                        %(balance_select)s                                                  AS balance,
                        COALESCE(account_tax.name->>%(lang)s, account_tax.name->>'en_US')   AS applied_tax,
                        account_tax.amount                                                  AS tax_amount,
                        - %(balance_select)s                                                AS amount_net,
                        - %(balance_select)s * account_tax.amount / 100                     AS amount_tax,
                        - %(balance_select)s * (1 + COALESCE(account_tax.amount, 0) / 100)  AS amount_total
                   FROM %(table_references)s
                        %(currency_table_join)s
              LEFT JOIN account_move_line_account_tax_rel AS aml_tax_rel ON  aml_tax_rel.account_move_line_id = account_move_line.id
              LEFT JOIN account_tax ON account_tax.id = aml_tax_rel.account_tax_id OR account_tax.id = account_move_line.tax_line_id
                  WHERE %(search_condition)s
                    AND account_move_line.move_id = %(invoice_id)s
                    AND account_move_line.display_type = 'product'
               GROUP BY account_move_line.id, account_currency_table.rate, account_tax.id
               ORDER BY account_move_line.id
            """,
            table_references=query.from_clause,
            search_condition=query.where_clause,
            balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
            currency_table_join=report._currency_table_aml_join(options),
            invoice_id=invoice_id,
            lang=self.env.lang,
        )
        self.env.cr.execute(query_to_execute)
        return self.env.cr.dictfetchall()

    def _get_invoice_aml_report_lines(self, report, options, invoice_line_id, aml_results, progress, level_shift=0):
        lines = []
        has_more = False
        treated_results_count = 0
        next_progress = progress
        for result in aml_results:
            if self._is_report_limit_reached(report, options, treated_results_count):
                # We loaded one more than the limit on purpose: this way we know we need a "load more" line
                has_more = True
                break

            new_line = self._get_invoice_aml_report_line(report, options, result, invoice_line_id, level_shift=level_shift)
            lines.append(new_line)
            next_progress = self._init_load_more_progress(options, new_line)
            treated_results_count += 1
        return {
            'lines': lines,
            'offset_increment': treated_results_count,
            'has_more': has_more,
            'progress': next_progress,
        }

    def _get_invoice_aml_report_line(self, report, options, result, invoice_line_id, level_shift=0):
        columns = []
        for column in options['columns']:
            col_expr_label = column['expression_label']

            if col_expr_label in ('partner_name', 'invoice_date', 'invoice_date_due', 'amount_in_currency'):
                col_value = ''
            else:
                if col_expr_label not in result:
                    raise UserError(self.env._("The column '%s' is not available for this report.", col_expr_label))
                col_value = result[col_expr_label]

            columns.append(report._build_column_dict(col_value, column, options=options))

        return {
            'id': report._get_generic_line_id('account.move.line', result['id'], parent_line_id=invoice_line_id),
            'parent_id': invoice_line_id,
            'name': result['name'],
            'columns': columns,
            'caret_options': 'account_move_line',
            'level': 3 + level_shift,
        }

    # ------------------------------------------------------
    # Construction of JPK FA
    # ------------------------------------------------------

    def _query_invoices(self, report, options):
        """ Query executed when downloading the XML file """
        report._init_currency_table(options)
        query = report._get_report_query(options, 'strict_range')
        clause_KSeF = SQL("(l10n_pl_edi_status != 'accepted' OR l10n_pl_edi_status IS NULL)")
        query_to_execute = SQL(
            """
                 SELECT account_move_line.id,
                        account_move_line.name,
                        account_move_line.currency_id,
                        account_move_line.amount_currency,
                        account_move_line.display_type,
                        account_move_line.quantity,
                        account_move_line.price_unit,
                        account_move_line.price_subtotal,
                        account_move_line.price_total,
                        account_move_line.discount,
                        %(balance_select)s                      AS balance,
                        account_move.id                         AS move_id,
                        account_move.name                       AS move_name,
                        account_move.amount_total,
                        account_move.amount_total_signed,
                        account_move.invoice_date,
                        account_move.invoice_date_due,
                        account_move.delivery_date,
                        currency.name                           AS currency_name,
                        partner.name                            AS partner_name,
                        partner.contact_address_complete        AS partner_address,
                        partner.vat                             AS partner_vat,
                        account_tax.amount                      AS tax_rate,
                        account_tax.name                        AS tax_name
                   FROM %(table_references)s
                   JOIN account_move ON account_move.id = account_move_line.move_id
              LEFT JOIN res_partner partner ON partner.id = account_move_line.partner_id
              LEFT JOIN res_company company ON company.id = account_move_line.company_id
              LEFT JOIN res_currency currency ON currency.id = account_move.currency_id
              LEFT JOIN account_move_line_account_tax_rel as aml_tax_rel ON  aml_tax_rel.account_move_line_id = account_move_line.id
              LEFT JOIN account_tax ON account_tax.id = aml_tax_rel.account_tax_id OR account_tax.id = account_move_line.tax_line_id
                        %(currency_table_join)s
                  WHERE %(search_condition)s
                    AND %(clause_KSeF)s
                    AND account_move.move_type IN ('out_invoice', 'out_refund')
                    AND account_move_line.display_type IN ('product', 'tax')
               GROUP BY account_move_line.id, account_move.id, account_currency_table.rate, currency.id, partner.id, account_tax.id
               ORDER BY account_move.invoice_date, account_move_line.id
            """,
            table_references=query.from_clause,
            search_condition=query.where_clause,
            balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
            currency_table_join=report._currency_table_aml_join(options),
            clause_KSeF=clause_KSeF,
        )
        self.env.cr.execute(query_to_execute)
        return self.env.cr.dictfetchall()

    def _prepare_values(self, options, values):
        company = self.env.company
        partner = self.env.company.partner_id
        country_code, vat = partner._split_vat(company.vat) if company.vat else (None, None)
        values.update({
            'date_now': fields.Date.to_string(fields.Date.context_today(self)),
            'date_to': fields.Date.from_string(options.get('date').get('date_to')),
            'date_from': fields.Date.from_string(options.get('date').get('date_from')),
            'company': company,
            'partner': partner,
            'country_prefix': country_code,
            'vat_without_country_prefix': vat,
        })
        return values

    def _fill_move_values(self, report, options, values):
        invoices = {}
        for res in self._query_invoices(report, options):
            invoices.setdefault(res['move_id'], {
                'move_name': res['move_name'],
                'invoice_date': res['invoice_date'],
                'invoice_date_due': res['invoice_date_due'],
                'delivery_date': res['delivery_date'],
                'amount_total': res['amount_total_signed'],
                'amount_total_in_currency': res['amount_total'],
                'partner_name': res['partner_name'],
                'partner_address': res['partner_address'],
                'currency_name': res['currency_name'],
                'move_product_lines': [],
                'tax_detail': {
                    tax_group_id: defaultdict(float) for tax_group_id in ['23', '8', '5', '0', 'other']
                },
                'number_invoice_lines_except_tax': 0,
                'total_net_amount': 0.0,
                'total_net_amount_in_PLN': 0.0,
                'total_gross_amount': 0.0,
                'total_gross_amount_in_PLN': 0.0,
            })

            if res['partner_vat']:
                country_code, vat = self.env.company.partner_id._split_vat(res['partner_vat'])
                invoices[res['move_id']].update({
                    'partner_vat': res['partner_vat'],
                    'country_prefix': country_code,
                    'vat_without_country_prefix': vat,
                })

            tax_group = self._get_tax_group(res['tax_rate'])
            invoice = invoices[res['move_id']]

            invoice['total_gross_amount'] -= res['amount_currency']
            invoice['total_gross_amount_in_PLN'] -= res['balance']

            if res['display_type'] == 'tax':
                invoice['tax_detail'][tax_group]['tax_amount'] -= res['amount_currency']
                invoice['tax_detail'][tax_group]['tax_amount_in_PLN'] -= res['balance']
            else:
                invoice['number_invoice_lines_except_tax'] += 1
                invoice['tax_detail'][tax_group]['net_amount'] -= res['amount_currency']
                invoice['total_net_amount'] -= res['amount_currency']
                invoice['tax_detail'][tax_group]['net_amount_in_PLN'] -= res['balance']
                invoice['total_net_amount_in_PLN'] -= res['balance']
                invoice['move_product_lines'].append(res)

        self._fill_additional_values(invoices)
        values.update({
            'invoices': invoices,
            'number_invoices': len(invoices),
            'total_amount_invoices': sum(invoice['total_gross_amount'] for invoice in invoices.values()),
            'number_invoice_lines': sum(invoice['number_invoice_lines_except_tax'] for invoice in invoices.values()),
        })

    def _get_tax_group(self, tax_rate):
        TAX_MAPPING = {
            (22, 23): '23',
            (7, 8): '8',
            (5.0, 5.0): '5',
            (0.0, 0.0): '0'
        }
        if not tax_rate:
            return '0'
        tax_group = 'other'
        for (low, high), group in TAX_MAPPING.items():
            if low <= tax_rate <= high:
                tax_group = group
                break
        return tax_group

    def _fill_additional_values(self, invoices):
        """
        Computes field P_19 and invoice type fields
        """
        invoice_ids = tuple(invoices.keys()) or (0,)
        query = SQL("""
                SELECT account_move.id,
                       reversed.name
                  FROM account_move
                  JOIN account_move reversed ON account_move.reversed_entry_id = reversed.id
                 WHERE account_move.id IN %(invoice_ids)s
                   AND account_move.move_type = 'out_refund'
                   AND account_move.state = 'posted'
                   AND reversed.state = 'posted'
              GROUP BY account_move.id, reversed.name
        """,
            invoice_ids=invoice_ids,
        )
        self.env.cr.execute(query)
        invoice2reverse = {move_id: {
            'reversed_move_name': reversed_move_name,
        } for move_id, reversed_move_name in self.env.cr.fetchall()}
        for invoice_id, invoice in invoices.items():
            # P_19 : Equals True if Tax Reporting Code VAT EXEMPT of ORA_PL_JPK_TAX_TYPE type is assigned to one
            # of the Tax Rates in the invoice.
            invoice['vat_exempt'] = any("Exempt" in (line.get('tax_name') or {}).get('en_US', '') for line in invoice['move_product_lines'])
            if invoice_id in invoice2reverse:
                invoice.update({
                    'type': "KOREKTA",
                    'inverted_invoice': invoice2reverse[invoice_id]['reversed_move_name'],
                })
            else:
                invoice['type'] = 'VAT'

    def _fill_values_errors(self):
        values = dict()
        company = self.env.company
        if not company.l10n_pl_reports_tax_office_id:
            values.setdefault('errors', {})['tax_office_id'] = {
                'message': self.env._("Please configure the tax office in the Accounting Settings."),
                'action_text': self.env._("Settings"),
                'action': self.env['res.config.settings']._get_records_action(name="Settings"),
            }
        if not company.vat:
            values.setdefault('errors', {})['tax_office_id'] = {
                'message': self.env._("Please configure the vat number in the company's contact."),
                'action_text': self.env._("Company"),
                'action': company._get_records_action(name="Company"),
            }
        return values

    def export_tax_report_to_xml(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        values = self._fill_values_errors()
        self._prepare_values(options, values)
        self._fill_move_values(report, options, values)
        file_data = report._generate_file_data_with_error_check(
            options,
            self.env['ir.qweb']._render,
            {'values': values, 'template': 'l10n_pl_reports_jpk_fa.jpk_fa_export_template', 'file_type': 'xml'},
            values.get('errors', {}),
        )
        return file_data

    def print_jpk_fa_xml(self, options):
        return {
            'type': 'ir_actions_account_report_download',
            'data': {
                'model': self.env.context.get('model'),
                'options': json.dumps(options),
                'file_generator': 'export_tax_report_to_xml',
            }
        }
