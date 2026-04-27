from odoo import api, fields, models, _
from odoo.tools import date_utils, SQL

L10N_MA_CUSTOMS_VAT_ICE = '20727020'


class MoroccanTaxReportCustomHandler(models.AbstractModel):
    _name = 'l10n_ma.tax.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'Moroccan Tax Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        options.setdefault('buttons', []).append({
            'name': _('XML'),
            'sequence': 30,
            'action': 'export_file',
            'action_param': 'l10n_ma_reports_export_vat_to_xml',
            'file_export_type': _('XML'),
        })

    @api.model
    def _l10n_ma_prepare_vat_report_header_values(self, company, bill_data_list, period_type, date_from):
        template_vals = {
            'errors': {},
            'year': str(date_from.year),
        }
        if period_type == 'trimester':
            template_vals['period'] = date_utils.get_quarter_number(date_from)
            template_vals['regime_code'] = '2'
        else:
            template_vals['period'] = date_from.month
            template_vals['regime_code'] = '1'

        template_vals['vat_id'] = company.vat

        #  Check for different errors in the report
        incomplete_vendor_ids = [data['partner_id'] for data in bill_data_list if data['partner_from_ma'] and (not data['partner_vat'] or not data['partner_ice'])]
        self._check_l10n_ma_report_errors(self.env['res.partner'].browse(incomplete_vendor_ids), period_type, template_vals, company)
        return template_vals

    def _check_l10n_ma_report_errors(self, errored_vendors, period_type, template_vals, company):
        if errored_vendors:
            template_vals['errors']['partner_vat_ice_missing'] = {
                'message': _('There are partners located in Morocco without any ICE and/or Tax ID specified.'
                             ' The resulting XML will not contain the associated vendor bills.'),
                'action_text': _('View Partner(s)'),
                'action': errored_vendors._get_records_action(name=_('Invalid Partner(s)')),
            }

        if period_type not in {'monthly', 'trimester'}:
            template_vals['errors']['period_invalid'] = {
                'message': _('This report only supports monthly and quarterly periods.'),
                'level': 'danger',
            }

        if not company.vat:
            template_vals['errors']['company_vat_missing'] = {
                'message': _('Company %s has no VAT number and it is required to generate the XML file.', company.name),
                'action_text': _('View Company/ies'),
                'action': company.partner_id._get_records_action(name=_('Invalid Company/ies')),
                'level': 'danger',
            }

    @api.model
    def _l10n_ma_prepare_vat_report_bill_values(self, bill_data_list, prorata_value):
        template_vals = {
            'bills': [],
        }

        if int(prorata_value):
            template_vals['prorata'] = prorata_value

        index = 1
        for bill_data in bill_data_list:
            if bill_data['partner_from_ma'] and not (bill_data['partner_vat'] and bill_data['partner_ice']):
                continue

            sign = -1 if bill_data['is_inbound'] else 1

            payment_methods = [method for method in (bill_data['payment_method'] or []) if method is not None]
            base_amount = self.env.company.currency_id.round(bill_data['tax_amount'] / (bill_data['tax_rate'] / 100))

            template_vals['bills'].append({
                'name': bill_data['move_name'],
                'sequence': index,
                'base_amount': base_amount * sign,
                'tax_amount': bill_data['tax_amount'] * sign,
                'total_amount': self.env.company.currency_id.round((bill_data['tax_amount'] + base_amount) * sign),
                'partner_vat': bill_data['partner_vat'] or L10N_MA_CUSTOMS_VAT_ICE,
                'partner_name': bill_data['partner_name'],
                'partner_ice': bill_data['partner_ice'] or L10N_MA_CUSTOMS_VAT_ICE,
                'tax_rate': bill_data['tax_rate'] * sign,
                'payment_method': payment_methods[0] if len(payment_methods) == 1 else '7',
                'payment_date':  bill_data['payment_date'] or '',
                'invoice_date': bill_data['invoice_date'],
            })

            index += 1

        return template_vals

    @api.model
    def _l10n_ma_prepare_vat_report_values(self, options):
        report = self.env['account.report'].browse(options['report_id'])

        deductions_expr = self.env.ref('l10n_ma.tax_report_part_d_tax_sum')
        tags = deductions_expr._expand_aggregations()._get_matching_tags()
        report_query = report._get_report_query(options, 'strict_range', domain=[('tax_tag_ids', 'in', tags.ids)])

        if 'account_move_line__move_id' not in report_query._joins:
            report_query.join('account_move_line', 'move_id', 'account_move', 'id', 'move_id')
        if 'account_move_line__partner_id' not in report_query._joins:
            report_query.left_join('account_move_line', 'partner_id', 'res_partner', 'id', 'partner_id')

        self._cr.execute(SQL(
            """
            SELECT
                COALESCE(MIN(caba_origin_move.name), MIN(account_move_line__move_id.name)) AS move_name,
                SUM(account_move_line.balance) AS tax_amount,
                CASE WHEN account_move_line__partner_id.country_id = %(ma_country_id)s
                    THEN account_move_line__partner_id.vat
                    ELSE account_move_line__partner_id.l10n_ma_customs_vat
                END AS partner_vat,
                account_move_line__partner_id.name as partner_name,
                account_move_line__partner_id.company_registry AS partner_ice,
                tax.amount AS tax_rate,
                CASE WHEN MIN(caba_origin_move.id) IS NULL
                    THEN NULL
                    ELSE ARRAY_AGG(DISTINCT caba_payment.l10n_ma_reports_payment_method)
                END AS payment_method,
                CASE WHEN MIN(caba_origin_move.id) IS NULL
                    THEN NULL -- We make the assumption it's not important to provide it if not using cash basis
                    ELSE GREATEST(MAX(account_move_line__move_id.date), MAX(caba_origin_move.date))
                END AS payment_date,
                COALESCE(MIN(caba_origin_move.invoice_date), MIN(account_move_line__move_id.invoice_date)) AS invoice_date,
                COALESCE(MIN(caba_origin_move.move_type), MIN(account_move_line__move_id.move_type)) IN %(inbound_types)s AS is_inbound,
                account_move_line__partner_id.country_id = %(ma_country_id)s AS partner_from_ma,
                account_move_line__partner_id.id AS partner_id

            FROM
                %(table_references)s
                JOIN account_tax tax
                    ON tax.id = account_move_line.tax_line_id -- Only tax lines receive tags from the report, so it's fine to do this
                    AND tax.amount_type = 'percent'
                LEFT JOIN account_move caba_origin_move
                    ON caba_origin_move.id = account_move_line__move_id.tax_cash_basis_origin_move_id
                LEFT JOIN account_partial_reconcile caba_partial
                    ON account_move_line__move_id.tax_cash_basis_rec_id = caba_partial.id
                LEFT JOIN account_move_line caba_payment_aml
                    ON caba_payment_aml.id IN (caba_partial.debit_move_id, caba_partial.credit_move_id)
                    AND caba_payment_aml.move_id != caba_origin_move.id
                LEFT JOIN account_payment caba_payment
                    ON caba_payment.move_id = caba_payment_aml.move_id

            WHERE %(search_condition)s

            GROUP BY account_move_line__partner_id.id, COALESCE(caba_origin_move.id, account_move_line__move_id.id), tax.id
            """,
            table_references=report_query.from_clause,
            search_condition=report_query.where_clause,
            ma_country_id=self.env.ref('base.ma').id,
            inbound_types=tuple(self.env['account.move'].get_inbound_types()),
        ))

        bill_data_list = self.env.cr.dictfetchall()

        date_from = fields.Date.from_string(options['date'].get('date_from'))
        period_type = options['tax_periodicity']['periodicity']
        template_vals = self._l10n_ma_prepare_vat_report_header_values(self.env.company, bill_data_list, period_type, date_from)

        prorata_expression = self.env.ref('l10n_ma.l10n_ma_vat_d_prorata_pro')
        prorata_expr_totals = report._compute_expression_totals_for_each_column_group(prorata_expression, options)
        prorata_value = prorata_expr_totals[next(iter(options['column_groups']))][prorata_expression]['value']
        template_vals |= self._l10n_ma_prepare_vat_report_bill_values(bill_data_list, prorata_value)

        return template_vals

    @api.model
    def l10n_ma_reports_export_vat_to_xml(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        template_values = self._l10n_ma_prepare_vat_report_values(options)
        return report._generate_file_data_with_error_check(
            options,
            self.env['ir.qweb']._render,
            {'values': template_values, 'template': 'l10n_ma_reports.l10n_ma_tax_report_template', 'file_type': 'xml'},
            template_values['errors'],
        )
