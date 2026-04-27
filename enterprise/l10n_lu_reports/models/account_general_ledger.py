# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from itertools import groupby

from odoo.tools import get_lang, SQL

from odoo import api, models, _


class AccountGeneralLedger(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)
        if self.env.company.account_fiscal_country_id.code == 'LU':
            options.setdefault('buttons', []).append({
                'name': _('FAIA'),
                'sequence': 50,
                'action': 'export_file',
                'action_param': 'l10n_lu_export_saft_to_xml',
                'file_export_type': _('XML')
            })

    @api.model
    def _fill_l10n_lu_saft_report_invoices_values(self, options, values):
        def get_product_action(message, product_ids, level='warning'):
            return {
                'message': message,
                'action_text': _('View Products'),
                'action': self.env['product.product'].browse(product_ids)._get_records_action(name=_("Invalid Products")),
                'level': level,
            }

        def _get_product_vals_list(values, encountered_product_ids):
            product_template_name = self.env['product.template']._field_to_sql('product_template', 'name')
            uom_name = self.env['uom.uom']._field_to_sql('uom', 'name')
            base_uom_name = self.env['uom.uom']._field_to_sql('base_uom', 'name')
            self._cr.execute(SQL(
                '''
                SELECT
                    product.id,
                    product.barcode,
                    %(product_template_name)s             AS name,
                    product.product_tmpl_id,
                    product.default_code,
                    product_category.name               AS product_category,
                    %(uom_name)s                        AS standard_uom,
                    uom.uom_type                        AS uom_type,
                    TRUNC(uom.factor, 8)                AS uom_ratio,
                    CASE
                        WHEN uom.factor != 0
                        THEN TRUNC((1.0 / uom.factor), 8)
                        ELSE 0
                    END                                 AS ratio,
                    %(base_uom_name)s                   AS base_uom
                FROM product_product product
                    LEFT JOIN product_template          ON product_template.id = product.product_tmpl_id
                    LEFT JOIN product_category          ON product_category.id = product_template.categ_id
                    LEFT JOIN uom_uom uom               ON uom.id = product_template.uom_id
                    LEFT JOIN uom_uom base_uom          ON base_uom.category_id = uom.category_id AND base_uom.uom_type='reference'
                WHERE product.id in %(encountered_product_ids)s
                ORDER BY default_code
                ''',
                product_template_name=product_template_name,
                uom_name=uom_name,
                base_uom_name=base_uom_name,
                encountered_product_ids=tuple(encountered_product_ids)
            ))

            product_vals_list = self._cr.dictfetchall()
            duplicate_product_ids = set()
            empty_product_ids = set()
            for product_code, grouped_products in groupby(product_vals_list, key=lambda product: product['default_code']):
                product_list = list(grouped_products)
                if not product_code:
                    empty_product_ids.update(product_list_item['id'] for product_list_item in product_list)
                elif len(product_list) > 1:
                    for product in product_list:
                        duplicate_product_ids.add(product['id'])
            if duplicate_product_ids:
                values['errors']['product_duplicate_ref'] = get_product_action(
                    _("Some products have duplicate 'Internal Reference', please make them unique."),
                    list(duplicate_product_ids),
                    level='danger'
                )
            if empty_product_ids:
                values['errors']['product_missing_ref'] = get_product_action(
                    _("Some products are missing `Internal Reference`, please define them."),
                    list(empty_product_ids),
                    level='danger'
                )
            return product_vals_list

        res = {
            'total_invoices_debit': 0.0,
            'total_invoices_credit': 0.0,
            'total_bills_debit': 0.0,
            'total_bills_credit': 0.0,
            'invoice_vals_list': [],
            'uoms': [],
            'product_vals_list': [],
        }

        # Fill 'total_invoices_debit', 'total_invoices_credit', 'total_bills_debit', 'total_bills_credit', 'invoice_vals_list'.
        encountered_product_ids = set()
        encountered_product_uom_ids = set()

        # TODO: to remove in master, do not include the in_invoice if the template was not updated
        template_tree = self.env['ir.qweb']._load('l10n_lu_reports.saft_template_inherit_l10n_lu_saft')[0]
        missing_tree_node = template_tree.findall('.//PurchaseInvoices')

        for move_vals in values['move_vals_list']:

            if move_vals['type'] not in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'):
                continue

            # TODO: to remove in master, do not include the in_invoice if the template was not updated
            if not missing_tree_node and move_vals['type'] not in ('out_invoice', 'out_refund'):
                continue

            move_vals.update({
                'invoice_line_vals_list': [],
                'tax_detail_vals_list': [],
                'total_invoice_untaxed_balance': 0.0,
                'total_invoice_tax_balance': 0.0,
            })

            for line_vals in move_vals['line_vals_list']:
                if line_vals['tax_line_id']:
                    move_vals['tax_detail_vals_list'].append({
                        'currency_id': line_vals['currency_id'],
                        'currency_code': line_vals['currency_code'],
                        'tax_id': line_vals['tax_line_id'],
                        'tax_name': line_vals['tax_name'],
                        'tax_amount': line_vals['tax_amount'],
                        'tax_base_amount': line_vals['tax_base_amount'],
                        'tax_amount_type': line_vals['tax_amount_type'],
                        'amount': line_vals['balance'],
                        'amount_currency': line_vals['amount_currency'],
                        'rate': line_vals['rate'],
                    })
                    move_vals['total_invoice_tax_balance'] -= line_vals['balance']
                elif not line_vals['account_type'] in ('asset_receivable', 'liability_payable') and line_vals['display_type'] == 'product':
                    move_vals['total_invoice_untaxed_balance'] -= line_vals['balance']
                    if line_vals['balance'] > 0.0:
                        total_debit_key = 'total_invoices_debit' if move_vals['type'] in ('out_invoice', 'out_refund') else 'total_bills_debit'
                        res[total_debit_key] += line_vals['balance']
                    else:
                        total_credit_key = 'total_invoices_credit' if move_vals['type'] in ('out_invoice', 'out_refund') else 'total_bills_credit'
                        res[total_credit_key] -= line_vals['balance']
                    if line_vals['product_id']:
                        encountered_product_ids.add(line_vals['product_id'])
                    if line_vals['product_uom_id']:
                        encountered_product_uom_ids.add(line_vals['product_uom_id'])
                    move_vals['invoice_line_vals_list'].append(line_vals)

            res['invoice_vals_list'].append(move_vals)
            move_vals['total_invoice_balance'] = move_vals['total_invoice_untaxed_balance'] + move_vals['total_invoice_tax_balance']

        # Fill 'uoms'.
        uoms = self.env['uom.uom'].browse(list(encountered_product_uom_ids))
        non_ref_uoms = uoms.filtered(lambda uom: uom.uom_type != 'reference')
        if non_ref_uoms:
            # search base UoM for UoM master table
            uoms |= self.env['uom.uom'].search([('category_id', 'in', non_ref_uoms.category_id.ids), ('uom_type', '=', 'reference')])
        res['uoms'] = uoms

        # Fill 'product_vals_list'.
        if len(encountered_product_ids) > 0:
            res['product_vals_list'] = _get_product_vals_list(values, encountered_product_ids)
        values.update(res)

    @api.model
    def _l10n_lu_prepare_saft_report_values(self, report, options):
        template_vals = self._saft_prepare_report_values(report, options)

        template_vals.update({
            'xmlns': 'urn:OECD:StandardAuditFile-Taxation/2.00',
            'file_version': '2.01',
            'accounting_basis': 'Invoice Accounting',
        })
        self._fill_l10n_lu_saft_report_invoices_values(options, template_vals)
        return template_vals

    @api.model
    def l10n_lu_export_saft_to_xml(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        template_vals = self._l10n_lu_prepare_saft_report_values(report, options)
        file_data = report._generate_file_data_with_error_check(
            options,
            self.env['ir.qweb']._render,
            {'values': template_vals, 'template': 'l10n_lu_reports.saft_template_inherit_l10n_lu_saft', 'file_type': 'xml'},
            template_vals['errors'],
        )
        return file_data
