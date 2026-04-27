# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.osv import expression
from odoo.tools import SQL
from odoo.tools.float_utils import float_round

class AccountIntrastatServicesBeReportHandler(models.AbstractModel):
    _name = 'account.intrastat.services.be.report.handler'
    _inherit = 'account.intrastat.services.report.handler'
    _description = 'Intrastat BE Services Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)
        # is F01DGS or F02CMS ?
        if options.get('selected_variant_id') == self.env.ref('l10n_be_intrastat_services.intrastat_report_services_f01dgs').id:
            options['l10n_be_variant'] = 'F01DGS'
        else:
            options['l10n_be_variant'] = 'F02CMS'

    def _get_intrastat_report_query(self, report, options, current_groupby, query_params=None, offset=None, limit=None, warnings=None, order_by=True):
        """
        - Include non intrastat countries in F01DGS and F02CMS report

        - In the F01DGS declaration, the amounts deducted (credit notes, …) must be listed for each
          heading not only under the ordinary heading, but also separately under the corresponding
          heading ending with CN (entitled “of which amounts deducted (credit notes, …)”).
          Example:
          10/01/2024: company A in Belgium receives from company B in Argentina an invoice for sea
          transport of passengers for the amount of 500.000 €.
          20/02/2024: company A in Belgium receives from company B in Argentina a credit note on the
          invoice of 01/2024 for an amount of 20.000 €.
          In the F01DGS declaration for January 2024, company A therefore indicates the following:
          ┌─────────┬─────────┬──────────────┬──────────┬───────────────┬─────────────────┐
          │ Period  │ Heading │ Country code │ Currency │ Income amount │ Expenses amount │
          ╞═════════╪═════════╪══════════════╪══════════╪═══════════════╪═════════════════╡
          │ 01/2024 │ B2001   │ AR           │ EUR      │               │ 500 000         │
          └─────────┴─────────┴──────────────┴──────────┴───────────────┴─────────────────┘
          For February 2024, company A indicates the following:
          ┌─────────┬─────────┬──────────────┬──────────┬───────────────┬─────────────────┐
          │ Period  │ Heading │ Country code │ Currency │ Income amount │ Expenses amount │
          ╞═════════╪═════════╪══════════════╪══════════╪═══════════════╪═════════════════╡
          │ 02/2024 │ B2001   │ AR           │ EUR      │ 20 000        │                 │
          │ 02/2024 │ B2001CN │ AR           │ EUR      │ 20 000        │                 │
          └─────────┴─────────┴──────────────┴──────────┴───────────────┴─────────────────┘
          The amounts deducted included in heading B2001 “Sea transport of passengers” on the income
          side must also be stated separately in the corresponding heading B2001CN on the income side.
          These headings ending with CN are not applicable in the declaration F02CMS.
          Source: https://www.nbb.be/doc/dd/onegate/data/f01dgs-f02cms_manual_en.pdf

        - Wrap query in new select to get specific data if file export
        """
        # get country name from non intrastat partner also for F01DGS or F02CMS
        query_params = {
            **(query_params or {}),
            'country_table_join': SQL(
                "LEFT JOIN res_country country ON account_move.intrastat_country_id = country.id "
                "OR partner.country_id = country.id"
            ),
            'country_condition': SQL(""),
        }

        if options.get('l10n_be_variant') == 'F01DGS':
            is_refund_domain = [('move_id.move_type', 'in', ('in_refund', 'out_refund'))]
            if current_groupby == 'id':
                for i, domain in enumerate(options['forced_domain']):
                    if domain[0] == 'product_id.intrastat_code_id.code':
                        if domain[2].endswith('CN'):
                            # When extending a CN line, search for refunds only and add CN to returned code.
                            # and remove 'CN' from commodity_code in domain as no CN code exists in DB
                            options['forced_domain'][i] = (domain[0], domain[1], domain[2][:-2])
                            options['forced_domain'] = expression.AND([
                                options['forced_domain'],
                                is_refund_domain,
                            ])
                            query_params['commodity_code'] = SQL("concat(code.code, 'CN')")
                        break
                query = super()._get_intrastat_report_query(
                    report, options, current_groupby, query_params, offset, limit,
                    warnings=warnings, order_by=order_by,
                )
            else:
                normal_lines_query = super()._get_intrastat_report_query(
                    report, options, current_groupby, query_params, offset, limit,
                    warnings=warnings, order_by=False,
                )
                options['forced_domain'] = expression.AND([
                    options.get('forced_domain') or [],
                    is_refund_domain,
                    [('product_id.product_tmpl_id.type', '=', 'service')],
                ])
                query_params['commodity_code'] = SQL("concat(code.code, 'CN')")  # adds 'CN' to code
                cn_lines_query = super()._get_intrastat_report_query(
                    report, options, current_groupby, query_params,
                    warnings=warnings, order_by=order_by,
                )
                query = SQL('%s UNION %s', normal_lines_query, cn_lines_query)
        else:
            query = super()._get_intrastat_report_query(report, options, current_groupby, query_params,
                                                         offset, limit, warnings=warnings, order_by=order_by)

        if options.get('export_mode') == 'file':
            query = SQL(
                    """
                SELECT intrastat_lines.commodity_code AS commodity_code,
                       intrastat_lines.country_code AS country_code,
                       intrastat_lines.invoice_currency_name as invoice_currency_name,
                       SUM(CASE WHEN "system" = '29' THEN value ELSE 0 END) as income,
                       SUM(CASE WHEN "system" = '19' THEN value ELSE 0 END) as expense
                  FROM (%(inner_query)s) intrastat_lines
              GROUP BY country_code, commodity_code, invoice_currency_name
                """,
                inner_query=query,
            )

        return query

    def _build_intrastat_custom_domain_blocks(self, grouping_key_dict):
        res = super()._build_intrastat_custom_domain_blocks(grouping_key_dict)
        # get country name from non intrastat partner also for F01DGS or F02CMS
        res['country_code'] = expression.OR([
            res['country_code'],
            [('move_id.partner_id.country_id.code', '=', grouping_key_dict['country_code'])],
        ])
        return res

    @api.model
    def _be_intrastat_get_csv_file_content(self, options, results):
        file_content = ''
        for result in results:
            # The amount is expressed in EUR, even if the transaction is in another currency and
            # said currency is specified in the report.
            # The BNB spec is not clear about this, but every amount is in EUR in any other
            # belgian intrastat report so we assume it's the case here too.
            file_content += ';'.join([
                result.get('commodity_code') or '',
                result.get('country_code') or '',
                result.get('invoice_currency_name') or '',
                str(int(float_round(result['income'], 0))),
                str(int(float_round(result['expense'], 0))),
            ]) + '\n'
        return file_content

    @api.model
    def _be_intrastat_get_xml_file_content(self, options, results, company):
        file_content = self.env['ir.qweb']._render('l10n_be_intrastat_services.intrastat_services_report_export_xml', {
            'company': company,
            'items': results,
            'date': fields.Date.to_date(options['date']['date_from']).strftime('%Y-%m'),
            'code': options.get('l10n_be_variant'),
            'form': options.get('l10n_be_variant'),
        })
        return file_content
