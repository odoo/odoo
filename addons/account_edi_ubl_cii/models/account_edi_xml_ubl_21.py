# -*- coding: utf-8 -*-
from odoo import api, models


class AccountEdiXmlUBL21(models.AbstractModel):
    _name = "account.edi.xml.ubl_21"
    _inherit = 'account.edi.xml.ubl_20'
    _description = "UBL 2.1"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_ubl_21.xml"

    def _export_invoice_ecosio_schematrons(self):
        return {
            'invoice': 'org.oasis-open:invoice:2.1',
            'credit_note': 'org.oasis-open:creditnote:2.1',
        }

    def _export_invoice_vals(self, invoice):
        # EXTENDS account.edi.xml.ubl_20
        vals = super()._export_invoice_vals(invoice)

        vals.update({
            'AddressType_template': 'account_edi_ubl_cii.ubl_21_AddressType',
            'PaymentTermsType_template': 'account_edi_ubl_cii.ubl_21_PaymentTermsType',
            'PartyType_template': 'account_edi_ubl_cii.ubl_21_PartyType',
            'InvoiceLineType_template': 'account_edi_ubl_cii.ubl_21_InvoiceLineType',
            'CreditNoteLineType_template': 'account_edi_ubl_cii.ubl_21_CreditNoteLineType',
            'DebitNoteLineType_template': 'account_edi_ubl_cii.ubl_21_DebitNoteLineType',
            'InvoiceType_template': 'account_edi_ubl_cii.ubl_21_InvoiceType',
            'CreditNoteType_template': 'account_edi_ubl_cii.ubl_21_CreditNoteType',
            'DebitNoteType_template': 'account_edi_ubl_cii.ubl_21_DebitNoteType',
        })

        vals['vals'].update({
            'ubl_version_id': 2.1,
            'buyer_reference': invoice.commercial_partner_id.ref,
        })

        return vals

    @api.model
    def _get_customization_ids(self):
        return {
            'ubl_bis3': 'urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0',
            'nlcius': 'urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0',
            'ubl_sg': 'urn:cen.eu:en16931:2017#conformant#urn:fdc:peppol.eu:2017:poacc:billing:international:sg:3.0',
            'xrechnung': 'urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0',
            'ubl_a_nz': 'urn:cen.eu:en16931:2017#conformant#urn:fdc:peppol.eu:2017:poacc:billing:international:aunz:3.0',
            'pint_jp': 'urn:peppol:pint:billing-1@jp-1',
            'pint_sg': 'urn:peppol:pint:billing-1@sg-1',
            'pint_my': 'urn:peppol:pint:billing-1@my-1',
            'oioubl_21': 'OIOUBL-2.1',
        }

    def _get_selfbilling_customization_ids(self):
        return {
            'ubl_bis3': 'urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:selfbilling:3.0'
        }

    # -------------------------------------------------------------------------
    # EXPORT: New (dict_to_xml) helpers
    # -------------------------------------------------------------------------

    def _get_invoice_node(self, vals):
        document_node = super()._get_invoice_node(vals)

        if vals['document_type'] != 'invoice':
            # In UBL 2.1, Delivery, PaymentMeans, PaymentTerms exist also in DebitNote and CreditNote
            self._add_invoice_delivery_nodes(document_node, vals)
            self._add_invoice_payment_means_nodes(document_node, vals)
            self._add_invoice_payment_terms_nodes(document_node, vals)

        return document_node

    def _add_invoice_header_nodes(self, document_node, vals):
        super()._add_invoice_header_nodes(document_node, vals)

        invoice = vals['invoice']
        document_node.update({
            'cbc:UBLVersionID': {'_text': '2.1'},
            'cbc:DueDate': {'_text': invoice.invoice_date_due} if vals['document_type'] == 'invoice' else None,
            'cbc:CreditNoteTypeCode': {'_text': 381} if vals['document_type'] == 'credit_note' else None,
            'cbc:BuyerReference': {'_text': invoice.commercial_partner_id.ref},
        })

    def _add_document_allowance_charge_nodes(self, document_node, vals):
        super()._add_document_allowance_charge_nodes(document_node, vals)

        # AllowanceCharge exists in debit notes only in UBL 2.1
        if vals['document_type'] == 'debit_note':
            document_node['cac:AllowanceCharge'] = []
            for base_line in vals['base_lines']:
                if self._is_document_allowance_charge(base_line):
                    document_node['cac:AllowanceCharge'].append(
                        self._get_document_allowance_charge_node({
                            **vals,
                            'base_line': base_line,
                        })
                    )

    def _add_invoice_line_period_nodes(self, line_node, vals):
        base_line = vals['base_line']

        # deferred_start_date & deferred_end_date are enterprise-only fields
        if (
            vals['document_type'] in {'invoice', 'credit_note'}
            and (base_line.get('deferred_start_date') or base_line.get('deferred_end_date'))
        ):
            line_node['cac:InvoicePeriod'] = {
                'cbc:StartDate': {'_text': base_line['deferred_start_date']},
                'cbc:EndDate': {'_text': base_line['deferred_end_date']},
            }

    def _add_document_line_allowance_charge_nodes(self, line_node, vals):
        line_node['cac:AllowanceCharge'] = [self._get_line_discount_allowance_charge_node(vals)]
        if vals['fixed_taxes_as_allowance_charges']:
            line_node['cac:AllowanceCharge'].extend(self._get_line_fixed_tax_allowance_charge_nodes(vals))
