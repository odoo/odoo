from odoo import models
from odoo.addons.account.tools import dict_to_xml
from odoo.addons.account_edi_ubl_cii.tools import CrossIndustryInvoice
from lxml import etree

import logging

_logger = logging.getLogger(__name__)

DEFAULT_FACTURX_DATE_FORMAT = '%Y%m%d'
CII_NAMESPACES = {
    'ram': "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    'rsm': "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    'udt': "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
}

# Imcomplete, full list on https://service.unece.org/trade/untdid/d16b/tred/tred4461.htm
PAYMENT_MEAN_CODES = {
    'Payment to bank account': 42,
    'SEPA direct debit': 59
}


class AccountEdiXmlCii(models.AbstractModel):
    _name = 'account.edi.xml.cii'
    _inherit = ['account.edi.cii']
    _description = "Factur-x/ZUGFeRD CII 2.2.0"

    def _find_value(self, xpath, tree, nsmap=False):
        # EXTENDS account.edi.common
        return super()._find_value(xpath, tree, CII_NAMESPACES)

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        if invoice.commercial_partner_id.country_code == 'DE':
            return f"{invoice.name.replace('/', '_')}_zugferd.xml"
        return f"{invoice.name.replace('/', '_')}_factur_x.xml"

    def _export_invoice_constraints(self, invoice, vals):
        constraints = self._invoice_constraints_common(invoice)
        constraints.update(
            self._cii_constraints(invoice, vals)
        )
        return constraints

    def _get_document_nsmap(self):
        return {
            'ram': "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
            'rsm': "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
            'udt': "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
            'qdt': "urn:un:unece:uncefact:data:standard:QualifiedDataType:100",
            'xsi': "http://www.w3.org/2001/XMLSchema-instance",
        }

    def _get_invoice_node(self, vals):
        self._cii_add_invoice_config_vals(vals)

        vals['document_node'] = document_node = {}
        self._cii_add_exchanged_document_context_node(vals)
        self._cii_add_exchanged_document_node(vals)
        self._cii_add_supply_chain_trade_transaction_node(vals)

        return document_node

    def _export_invoice(self, invoice):
        # Validate the structure of the taxes
        self._validate_taxes(invoice.invoice_line_ids.tax_ids)

        vals = {'invoice': invoice.with_context(lang=invoice.partner_id.lang)}
        document_node = self._get_invoice_node(vals)

        errors = [constraint for constraint in self._export_invoice_constraints(invoice, vals).values() if constraint]

        nsmap = self._get_document_nsmap()

        xml_content = dict_to_xml(document_node, nsmap=nsmap, template=CrossIndustryInvoice)

        return etree.tostring(xml_content, xml_declaration=True, encoding='UTF-8'), set(errors)

    # -------------------------------------------------------------------------
    # IMPORT
    # -------------------------------------------------------------------------

    def _get_import_document_amount_sign(self, tree):
        """
        In factur-x, an invoice has code 380 and a credit note has code 381. However, a credit note can be expressed
        as an invoice with negative amounts. For this case, we need a factor to take the opposite of each quantity
        in the invoice.
        """
        move_type_code = tree.find('.//{*}ExchangedDocument/{*}TypeCode')
        if move_type_code is None:
            return None, None
        if move_type_code.text == '381':
            return 'refund', 1
        if move_type_code.text == '380':
            amount_node = tree.find('.//{*}SpecifiedTradeSettlementHeaderMonetarySummation/{*}GrandTotalAmount')
            if amount_node is not None and float(amount_node.text) < 0:
                return 'refund', -1
            return 'invoice', 1
        return None, None

    def _import_invoice_ubl_cii(self, invoice, file_data, new=False):
        """
        :param account.move invoice:
        """
        if invoice.invoice_line_ids:
            return invoice._reason_cannot_decode_has_invoice_lines()
        return self._cii_import_invoice(invoice, file_data, new=new)

    def _import_prepare_missing_customer_create_values(self, collected_values):
        partner_create_values = super()._import_prepare_missing_customer_create_values(collected_values)

        customer_values = collected_values['customer_values']
        if (
                (routing_scheme := customer_values.get('routing_scheme'))
                and (routing_endpoint := customer_values.get('routing_endpoint'))
        ):
            partner_create_values['routing_scheme'] = routing_scheme
            partner_create_values['routing_endpoint'] = routing_endpoint

        return partner_create_values
