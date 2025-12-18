from odoo import _, api, models
from odoo.addons.account.tools import dict_to_xml
from odoo.tools import frozendict, html2plaintext
from odoo.tools.misc import formatLang, NON_BREAKING_SPACE

from lxml import etree


class AccountEdiUBLBis3InvoiceCommon(models.AbstractModel):
    _name = "account.edi.ubl.bis3.invoice_common"
    _inherit = ['account.edi.ubl.bis3', 'account.edi.ubl.invoice_common']
    _description = "Base helpers for UBL Invoice BIS3"

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_ubl_bis3.xml"

    # -------------------------------------------------------------------------
    # EXPORT: Building nodes
    # -------------------------------------------------------------------------

    def _ubl_add_document_currency_code_node(self, vals):
        # OVERRIDE
        self._ubl_add_document_currency_code_node_foreign_currency(vals)

    def _ubl_add_tax_currency_code_node(self, vals):
        # OVERRIDE
        self._ubl_add_tax_currency_code_node_company_currency_if_foreign_currency(vals)

    def _ubl_add_payment_means_nodes(self, vals):
        # EXTENDS
        super()._ubl_add_payment_means_nodes(vals)
        nodes = vals['document_node']['cac:PaymentMeans']

        invoice = vals['invoice']
        if invoice.move_type == 'out_invoice':
            if invoice.partner_bank_id:
                payment_means_code, payment_means_name = 30, 'credit transfer'
            else:
                payment_means_code, payment_means_name = 'ZZZ', 'mutually defined'
        else:
            payment_means_code, payment_means_name = 57, 'standing agreement'

        # TODO: This override is probably no longer necessary
        # in Denmark payment code 30 is not allowed. we hardcode it to 1 ("unknown") for now
        # as we cannot deduce this information from the invoice
        customer = vals['customer']['commercial_partner']
        if customer.country_code == 'DK':
            payment_means_code, payment_means_name = 1, 'unknown'

        partner_bank_vals = vals['partner_bank']
        payment_means_node = {
            'cbc:PaymentMeansCode': {
                '_text': payment_means_code,
                'name': payment_means_name,
            },
            'cbc:PaymentID': {'_text': invoice.payment_reference or invoice.name},
        }

        if partner_bank_vals:
            payment_means_node['cac:PayeeFinancialAccount'] = self._ubl_get_payment_means_payee_financial_account_node_from_partner_bank(vals, partner_bank_vals)
        else:
            payment_means_node['cac:PayeeFinancialAccount'] = None

        nodes.append(payment_means_node)



    # -------------------------------------------------------------------------
    # EXPORT: Preparing values
    # -------------------------------------------------------------------------

    def _export_invoice_prepare_values(self, vals, invoice):
        super()._export_invoice_prepare_values(vals, invoice)
        AccountTax = self.env['account.tax']

        self._ubl_add_values_company(vals, invoice.company_id)
        self._ubl_add_values_currency(vals, invoice.currency_id)
        self._ubl_add_values_supplier(vals)
        self._ubl_add_values_customer(vals, invoice.partner_id)
        self._ubl_add_values_delivery(vals, invoice.partner_shipping_id or invoice.partner_id)
        self._ubl_add_values_partner_bank(vals, invoice.partner_bank_id)
        self._ubl_add_values_payment_term(vals, invoice.invoice_payment_term_id)

        # Negative price_unit are not allowed.
        self._ubl_turn_base_lines_price_unit_as_always_positive(vals)

        # Manage taxes for emptying.
        self._ubl_turn_emptying_taxes_as_new_base_lines(vals)

        # Global rounding of tax_details using 6 digits.
        company = vals['company']
        AccountTax._round_raw_total_excluded(vals['base_lines'], company)
        AccountTax._round_raw_total_excluded(vals['base_lines'], company, in_foreign_currency=False)
        AccountTax._add_and_round_raw_gross_total_excluded_and_discount(vals['base_lines'], company)
        AccountTax._add_and_round_raw_gross_total_excluded_and_discount(vals['base_lines'], company, in_foreign_currency=False)


class AccountEdiUBLBis3Invoice(models.AbstractModel):
    _name = "account.edi.ubl.bis3.invoice"
    _inherit = ['account.edi.ubl.bis3.invoice_common', 'account.edi.ubl.invoice']
    _description = "Base helpers for UBL Invoice BIS3"

    def _export_invoice(self, invoice):
        vals = self._ubl_init_values()
        self._export_invoice_prepare_values(vals, invoice)
        document_node = self._ubl_get_invoice_node(vals)

        # errors = [constraint for constraint in self._export_invoice_constraints_new(invoice, vals).values() if constraint]
        errors = []

        xml_content = dict_to_xml(document_node)
        return etree.tostring(xml_content, xml_declaration=True, encoding='UTF-8'), set(errors)
