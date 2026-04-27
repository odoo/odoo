# -*- coding: utf-8 -*-

import json
from lxml import etree
from lxml.objectify import fromstring
from odoo import fields, models, release, tools, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_repr
from odoo.tools.json import json_default
from odoo.tools.xml_utils import _check_with_xsd

IRAS_DIGITS = 2
IRAS_VERSION = 'IAFv2.0.0'
IRAS_XML_TEMPLATE = 'l10n_sg_reports.iras_audit_file_xml'
IRAS_XSD = 'l10n_sg_reports/data/iras_audit_file.xsd'


class IrasAuditFileWizard(models.TransientModel):
    _name = 'l10n.sg.reports.iaf.wizard'
    _description = "Singaporean IAF Report Wizard"

    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    export_type = fields.Selection([
        ('xml', 'XML'),
        ('txt', 'TXT'),
        ], string='Export Type', required=True, default='xml')

    def generate_iras(self):
        general_ledger_report = self.env.ref('account_reports.general_ledger_report')
        options = general_ledger_report.get_options(previous_options={'date': {
            'date_from': self.date_from,
            'date_to': self.date_to
        }
        })
        if self.export_type == 'xml':
            return general_ledger_report.l10n_sg_export_iras_audit_file_xml(options)
        return general_ledger_report.l10n_sg_export_iras_audit_file_txt(options)


class IrasAuditFile(models.Model):
    _inherit = 'account.report'

    def _l10n_sg_get_company_infos(self, date_from, date_to):
        """
        Generate the informations about the company for the IRAS Audit File
        """
        if not self.env.company.l10n_sg_unique_entity_number:
            raise UserError(_('Your company must have a UEN.'))
        if not self.env.company.vat:
            raise UserError(_('Your company must have a GSTNo.'))

        return {
            'CompanyName': self.env.company.name,
            'CompanyUEN': self.env.company.l10n_sg_unique_entity_number,
            'GSTNo': self.env.company.vat,
            'PeriodStart': date_from,
            'PeriodEnd': date_to,
            'IAFCreationDate': fields.Date.to_string(fields.Date.today()),
            'ProductVersion': release.product_name + release.version,
            'IAFVersion': IRAS_VERSION
        }

    def _l10n_sg_get_purchases_infos(self, date_from, date_to):
        """
        Generate purchases informations for the IRAS Audit File
        """
        purchases_lines = []
        purchase_total_sgd = 0.0
        gst_total_sgd = 0.0
        transaction_count_total = 0

        invoice_ids = self.env['account.move'].search([
            ('company_id', '=', self.env.company.id),
            ('move_type', 'in', ['in_invoice', 'in_refund']),
            ('state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to)
            ])

        for invoice in invoice_ids:
            lines_number = 0
            for lines in invoice.invoice_line_ids:
                lines_number += 1
                sign = -1 if invoice.move_type == 'in_refund' else 1
                tax_amount = lines.price_total - lines.price_subtotal
                tax_amount_company = invoice.currency_id._convert(tax_amount, invoice.company_id.currency_id, invoice.company_id, invoice.invoice_date or invoice.date)
                transaction_count_total += 1
                purchase_total_sgd += lines.balance
                gst_total_sgd += tax_amount

                if not invoice.partner_id.l10n_sg_unique_entity_number:
                    raise UserError(_('Your partner (%s) must have a UEN.', invoice.partner_id.name))
                purchases_lines.append({
                    'SupplierName': (invoice.partner_id.name or '')[:100],
                    'SupplierUEN': (invoice.partner_id.l10n_sg_unique_entity_number or '')[:16],
                    'InvoiceDate': fields.Date.to_string(invoice.l10n_sg_permit_number_date if invoice.l10n_sg_permit_number and invoice.l10n_sg_permit_number_date else invoice.invoice_date),
                    'InvoiceNo': (invoice.name or '')[:50],
                    'PermitNo': invoice.l10n_sg_permit_number[:20] if invoice.l10n_sg_permit_number else False,
                    'LineNo': str(lines_number),
                    'ProductDescription': ('[' + lines.product_id.default_code + '] ' + lines.product_id.name if lines.product_id.default_code else lines.product_id.name or '')[:250],
                    'PurchaseValueSGD': float_repr(lines.balance, IRAS_DIGITS),
                    'GSTValueSGD': float_repr((lines.price_total - lines.price_subtotal) / (lines.quantity or 1), IRAS_DIGITS),
                    'TaxCode': (lines.tax_ids and lines.tax_ids[0].name or ' ')[:20],
                    'FCYCode': (invoice.currency_id.name if invoice.currency_id and invoice.currency_id.name != 'SGD' else 'XXX')[:3],
                    'PurchaseFCY': float_repr(lines.price_subtotal, IRAS_DIGITS) if invoice.currency_id.name != 'SGD' else '0',
                    'GSTFCY': float_repr(sign * tax_amount_company, IRAS_DIGITS) if invoice.currency_id.name != 'SGD' else '0'
                })

        return {
            'lines': purchases_lines,
            'PurchaseTotalSGD': float_repr(purchase_total_sgd, IRAS_DIGITS),
            'GSTTotalSGD': float_repr(gst_total_sgd, IRAS_DIGITS),
            'TransactionCountTotal': str(transaction_count_total)
        }

    def _l10n_sg_get_sales_infos(self, date_from, date_to):
        """
        Generate sales informations for the IRAS Audit File
        """
        supply_lines = []
        supply_total_sgd = 0.0
        gst_total_sgd = 0.0
        transaction_count_total = 0

        invoice_ids = self.env['account.move'].search([
            ('company_id', '=', self.env.company.id),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to)
            ])

        for invoice in invoice_ids:
            lines_number = 0
            for lines in invoice.invoice_line_ids:
                lines_number += 1
                sign = -1 if invoice.move_type == 'out_refund' else 1
                tax_amount = lines.price_total - lines.price_subtotal
                tax_amount_company = invoice.currency_id._convert(tax_amount, invoice.company_id.currency_id, invoice.company_id, invoice.invoice_date or invoice.date)
                transaction_count_total += 1
                supply_total_sgd -= lines.balance
                gst_total_sgd += tax_amount

                if not invoice.partner_id.l10n_sg_unique_entity_number:
                    raise UserError(_('Your partner (%s) must have a UEN.', invoice.partner_id.name))
                supply_lines.append({
                    'CustomerName': (invoice.partner_id.name or '')[:100],
                    'CustomerUEN': (invoice.partner_id.l10n_sg_unique_entity_number or '')[:16],
                    'InvoiceDate': fields.Date.to_string(invoice.invoice_date),
                    'InvoiceNo': (invoice.name or '')[:50],
                    'LineNo': str(lines_number),
                    'ProductDescription': ('[' + lines.product_id.default_code + '] ' + lines.product_id.name if lines.product_id.default_code else lines.product_id.name or '')[:250],
                    'SupplyValueSGD': float_repr(-lines.balance, IRAS_DIGITS),
                    'GSTValueSGD': float_repr((lines.price_total - lines.price_subtotal) / (lines.quantity or 1), IRAS_DIGITS),
                    'TaxCode': (lines.tax_ids and lines.tax_ids[0].name or ' ')[:20],
                    'Country': invoice.partner_id.commercial_partner_id.country_id.code if invoice.invoice_origin and invoice.partner_id.commercial_partner_id.country_id.code != 'SG' else False,
                    'FCYCode': (invoice.currency_id.name if lines.currency_id and lines.currency_id.name != 'SGD' else 'XXX')[:3],
                    'SupplyFCY': float_repr(lines.price_subtotal, IRAS_DIGITS) if invoice.currency_id.name != 'SGD' else '0',
                    'GSTFCY': float_repr(sign * tax_amount_company, IRAS_DIGITS) if invoice.currency_id.name != 'SGD' else '0'
                })
        return {
            'lines': supply_lines,
            'SupplyTotalSGD': float_repr(supply_total_sgd, IRAS_DIGITS),
            'GSTTotalSGD': float_repr(gst_total_sgd, IRAS_DIGITS),
            'TransactionCountTotal': str(transaction_count_total)
        }

    def _l10n_sg_get_gldata(self, date_from, date_to):
        """
        Generate gldata for IRAS Audit File
        """
        gldata_lines = []
        total_debit = 0.0
        total_credit = 0.0
        transaction_count_total = 0
        glt_currency = 'SGD'

        company = self.env.company
        move_line_ids = self.env['account.move.line'].search([
            ('company_id', '=', company.id),
            ('date', '>=', date_from),
            ('date', '<=', date_to)
            ])

        options = self.get_options(previous_options={
            'unfold_all': True,
            'unfolded_lines': [],
            'date': {
                'mode': 'range',
                'date_from': fields.Date.from_string(date_from),
                'date_to': fields.Date.from_string(date_from)
            },
        })
        general_ledger_report = self.env.ref('account_reports.general_ledger_report')
        handler = self.env['account.general.ledger.report.handler']

        all_accounts = self.env['account.account'].search(self.env['account.account']._check_company_domain(company))
        initial_balances = handler._get_initial_balance_values(general_ledger_report, all_accounts.ids, options)
        report_values = handler._query_values(general_ledger_report, options)

        for account in all_accounts:
            if account.account_type == 'equity_unaffected':
                report_vals_by_col_group = dict(report_values).get(account, {'col_group': {'unaffected_earnings': {'balance': 0, 'amount_currency': 0, 'debit': 0, 'credit': 0}}})
                initial_bal = next(iter(report_vals_by_col_group.values()))['unaffected_earnings']
            else:
                _account, initial_bal_by_col_group = initial_balances[account.id]
                initial_bal = next(iter(initial_bal_by_col_group.values()))
            balance = initial_bal.get('balance', 0)
            gldata_lines.append({
                'TransactionDate': date_from,
                'AccountID': account.code,
                'AccountName': account.name,
                'TransactionDescription': 'OPENING BALANCE',
                'Name': False,
                'TransactionID': False,
                'SourceDocumentID': False,
                'SourceType': False,
                'Debit': float_repr(initial_bal.get('debit', 0), IRAS_DIGITS),
                'Credit': float_repr(initial_bal.get('credit', 0), IRAS_DIGITS),
                'Balance': float_repr(balance, IRAS_DIGITS),
            })
            for move_line_id in move_line_ids:
                if move_line_id.account_id.code == account.code:
                    balance = company.currency_id.round(balance + move_line_id.debit - move_line_id.credit)
                    total_credit += move_line_id.credit
                    total_debit += move_line_id.debit
                    transaction_count_total += 1
                    account_type_dict = dict(self.env['account.account']._fields['account_type']._description_selection(self.env))
                    # for exchange gain/loss journal items, source document should be the invoice/bill it is generated from
                    source_doc = move_line_id.move_id.invoice_origin
                    description = move_line_id.name
                    if move_line_id.move_id.journal_id == move_line_id.company_id.currency_exchange_journal_id:
                        # find all reconciled lines from exchange move, then find lines where the move_id is invoice/bill. Use payment if not found.
                        reconciled_lines = move_line_id.move_id.line_ids._all_reconciled_lines()
                        moves = reconciled_lines.move_id
                        invoice_move = moves.filtered(lambda x: x.is_invoice(include_receipts=True))[:1]
                        if invoice_move:
                            source_doc = invoice_move.name
                        else:
                            payment_move = moves.filtered(lambda x: x.payment_id)[:1]
                            source_doc = payment_move.name if payment_move else source_doc
                        description = move_line_id.move_id.ref or description
                    gldata_lines.append({
                        'TransactionDate': fields.Date.to_string(move_line_id.date),
                        'AccountID': move_line_id.account_id.code,
                        'AccountName': move_line_id.account_id.name,
                        'TransactionDescription': description,
                        'Name': move_line_id.partner_id.name if move_line_id.partner_id else False,
                        'TransactionID': move_line_id.move_id.name,
                        'SourceDocumentID': source_doc,
                        'SourceType': account_type_dict[move_line_id.account_id.account_type][:20],
                        'Debit': float_repr(move_line_id.debit, IRAS_DIGITS),
                        'Credit': float_repr(move_line_id.credit, IRAS_DIGITS),
                        'Balance': float_repr(balance, IRAS_DIGITS)
                    })
        return {
            'lines': gldata_lines,
            'TotalDebit': float_repr(total_debit, IRAS_DIGITS),
            'TotalCredit': float_repr(total_credit, IRAS_DIGITS),
            'TransactionCountTotal': str(transaction_count_total),
            'GLTCurrency': glt_currency
        }

    def _l10n_sg_get_generic_data(self, date_from, date_to):
        return {
            'Company': self._l10n_sg_get_company_infos(date_from, date_to),
            'Purchases': self._l10n_sg_get_purchases_infos(date_from, date_to),
            'Sales': self._l10n_sg_get_sales_infos(date_from, date_to),
            'GlData': self._l10n_sg_get_gldata(date_from, date_to)
        }

    def _l10n_sg_get_xml(self, options):
        """
        Generate the IRAS Audit File in xml format
        """
        qweb = self.env['ir.qweb']
        values = self._l10n_sg_get_generic_data(options['date']['date_from'], options['date']['date_to'])
        doc = qweb._render(IRAS_XML_TEMPLATE, values=values)
        with tools.file_open(IRAS_XSD, 'rb') as xsd:
            _check_with_xsd(doc, xsd)
        tree = fromstring(doc)
        return etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding='UTF-8')

    def _l10n_sg_txt_create_line(self, values):
        node = ''
        for value in values:
            node += (value if value else '') + '|'
        node += '\n'
        return node

    def _l10n_sg_txt_company_infos(self, values):
        node = 'CompInfoStart|\n'
        node += self._l10n_sg_txt_create_line(values.keys())
        node += self._l10n_sg_txt_create_line(values.values())
        node += 'CompInfoEnd|\n\n'
        return node

    def _l10n_sg_txt_purchases_infos(self, values):
        node = 'PurcDataStart|\n'
        node += self._l10n_sg_txt_create_line([
            'SupplierName',
            'SupplierUEN',
            'InvoiceDate',
            'InvoiceNo',
            'PermitNo',
            'LineNo',
            'ProductDescription',
            'PurchaseValueSGD',
            'GSTValueSGD',
            'TaxCode',
            'FCYCode',
            'PurchaseFCY',
            'GSTFCY'
        ])
        for line in values['lines']:
            node += self._l10n_sg_txt_create_line(line.values())
        node += 'PurcDataEnd|' + values['PurchaseTotalSGD'] + '|' + values['GSTTotalSGD'] + '|' + values['TransactionCountTotal'] + '|\n\n'
        return node

    def _l10n_sg_txt_sales_infos(self, values):
        node = 'SuppDataStart|\n'
        node += self._l10n_sg_txt_create_line([
            'CustomerName',
            'CustomerUEN',
            'InvoiceDate',
            'InvoiceNo',
            'LineNo',
            'ProductDescription',
            'SupplyValueSGD',
            'GSTValueSGD',
            'TaxCode',
            'Country',
            'FCYCode',
            'SupplyFCY',
            'GSTFCY'
        ])
        for line in values['lines']:
            node += self._l10n_sg_txt_create_line(line.values())
        node += 'SuppDataEnd|' + values['SupplyTotalSGD'] + '|' + values['GSTTotalSGD'] + '|' + values['TransactionCountTotal'] + '|\n\n'
        return node

    def _l10n_sg_txt_gldata_infos(self, values):
        node = 'GLDataStart|\n'
        node += self._l10n_sg_txt_create_line([
            'TransactionDate',
            'AccountID',
            'AccountName',
            'TransactionDescription',
            'Name',
            'TransactionID',
            'SourceDocumentID',
            'SourceType',
            'Debit',
            'Credit',
            'Balance'
        ])
        for line in values['lines']:
            node += self._l10n_sg_txt_create_line(line.values())
        node += 'GLDataEnd|' + values['TotalDebit'] + '|' + values['TotalCredit'] + '|' + values['TransactionCountTotal'] + '|' + values['GLTCurrency'] + '|\n\n'
        return node

    def _l10n_sg_get_txt(self, options):
        """
        Generate the IRAS Audit File in txt format
        """
        values = self._l10n_sg_get_generic_data(options['date']['date_from'], options['date']['date_to'])
        txt = self._l10n_sg_txt_company_infos(values['Company'])
        txt += self._l10n_sg_txt_purchases_infos(values['Purchases'])
        txt += self._l10n_sg_txt_sales_infos(values['Sales'])
        txt += self._l10n_sg_txt_gldata_infos(values['GlData'])
        return txt

    def l10n_sg_export_iras_audit_file_xml(self, options):
        """
        Print the IAF in xml format
        """
        return {
            'type': 'ir_actions_account_report_download',
            'data': {
                 'options': json.dumps(options, default=json_default),
                 'file_generator': 'l10n_sg_print_iras_audit_file_xml',
             }
        }

    def l10n_sg_print_iras_audit_file_xml(self, options):
        return {
            'file_name': 'iras_audit_file.xml',
            'file_content': self._l10n_sg_get_xml(options),
            'file_type': 'xml',
        }

    def l10n_sg_export_iras_audit_file_txt(self, options):
        """
        Print the IAF in txt format
        """
        return {
            'type': 'ir_actions_account_report_download',
            'data': {
                 'options': json.dumps(options, default=json_default),
                 'file_generator': 'l10n_sg_print_iras_audit_file_txt',
             }
        }

    def l10n_sg_print_iras_audit_file_txt(self, options):
        return {
            'file_name': 'iras_audit_file.txt',
            'file_content': self._l10n_sg_get_txt(options),
            'file_type': 'txt',
        }
