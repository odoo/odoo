# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from itertools import groupby

from odoo.tools import get_lang

from odoo import api, models, _


class AccountGeneralLedger(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
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
        def _get_product_action(message, product_ids, critical=False):
            return {
                'message': message,
                'action_text': _('View Products'),
                'action_name': 'action_open_products',
                'action_params': product_ids,
                'critical': critical,
            }

        def _get_product_vals_list(values, encountered_product_ids):
            lang = self.env.user.lang or get_lang(self.env).code
            product_template_name = f"COALESCE(product_template.name->>'{lang}', product_template.name->>'en_US')"
            uom_name = f"COALESCE(uom.name->>'{lang}', uom.name->>'en_US')"
            base_uom_name = f"COALESCE(base_uom.name->>'{lang}', base_uom.name->>'en_US')"
            self._cr.execute(f'''
                SELECT
                    product.id,
                    product.barcode,
                    {product_template_name}             AS name,
                    product.product_tmpl_id,
                    product.default_code,
                    product_category.name               AS product_category,
                    {uom_name}                          AS standard_uom,
                    uom.uom_type                        AS uom_type,
                    TRUNC(uom.factor, 8)                AS uom_ratio,
                    CASE
                        WHEN uom.factor != 0
                        THEN TRUNC((1.0 / uom.factor), 8)
                        ELSE 0
                    END                                 AS ratio,
                    {base_uom_name}                     AS base_uom
                FROM product_product product
                    LEFT JOIN product_template          ON product_template.id = product.product_tmpl_id
                    LEFT JOIN product_category          ON product_category.id = product_template.categ_id
                    LEFT JOIN uom_uom uom               ON uom.id = product_template.uom_id
                    LEFT JOIN uom_uom base_uom          ON base_uom.category_id = uom.category_id AND base_uom.uom_type='reference'
                WHERE product.id in %s
                ORDER BY default_code
            ''', [tuple(encountered_product_ids)])

            product_vals_list = self._cr.dictfetchall()
            duplicate_product_ids = set()
            empty_product_ids = set()
            for product_code, grouped_products in groupby(product_vals_list, key=lambda product: product['default_code']):
                product_list = list(grouped_products)
                if not product_code:
                    empty_product_ids.add(product_list[0]['id'])
                elif len(product_list) > 1:
                    for product in product_list:
                        duplicate_product_ids.add(product['id'])
            if duplicate_product_ids:
                values['errors'].append(_get_product_action(
                    _("Some products have duplicate 'Internal Reference', please make them unique."),
                    list(duplicate_product_ids),
                    critical=True
                ))
            if empty_product_ids:
                values['errors'].append(_get_product_action(
                    _("Some products are missing `Internal Reference`, please define them."),
                    list(empty_product_ids),
                    critical=True
                ))
            return product_vals_list

        res = {
            'total_invoices_debit': 0.0,
            'total_invoices_credit': 0.0,
            'invoice_vals_list': [],
            'uoms': [],
            'product_vals_list': [],
        }

        # Fill 'total_invoices_debit', 'total_invoices_credit', 'invoice_vals_list'.
        encountered_product_ids = set()
        encountered_product_uom_ids = set()
        for move_vals in values['move_vals_list']:
            if move_vals['type'] not in ('out_invoice', 'out_refund'):
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
                        'tax_id': line_vals['tax_line_id'],
                        'tax_name': line_vals['tax_name'],
                        'tax_amount': line_vals['tax_amount'],
                        'tax_amount_type': line_vals['tax_amount_type'],
                        'amount': line_vals['balance'],
                        'amount_currency': line_vals['amount_currency'],
                        'rate': line_vals['rate'],
                    })
                    move_vals['total_invoice_tax_balance'] -= line_vals['balance']
                elif not line_vals['account_type'] in ('asset_receivable', 'liability_payable') and line_vals['display_type'] == 'product':
                    move_vals['total_invoice_untaxed_balance'] -= line_vals['balance']
                    if line_vals['balance'] > 0.0:
                        res['total_invoices_debit'] += line_vals['balance']
                    else:
                        res['total_invoices_credit'] -= line_vals['balance']
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
        file_data = self._saft_generate_file_data_with_error_check(
            report, options, template_vals, 'l10n_lu_reports.saft_template_inherit_l10n_lu_saft'
        )
        self.env['ir.attachment'].l10n_lu_reports_validate_xml_from_attachment(file_data['file_content'], 'saft')
        return file_data
