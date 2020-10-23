# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.osv import expression

import base64


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    ####################################################
    # Account.edi.format override
    ####################################################

    def _is_compatible_with_journal(self, journal):
        self.ensure_one()
        res = super()._is_compatible_with_journal(journal)
        if self.code != 'nlcius_1':
            return res
        return journal.type == 'sale' and journal.country_code == 'NL'

    def _post_invoice_edi(self, invoices, test_mode=False):
        self.ensure_one()
        if self.code != 'nlcius_1':
            return super()._post_invoice_edi(invoices, test_mode=test_mode)

        invoice = invoices  # no batch ensure that there is only one invoice
        attachment = self._export_nlcius(invoice)
        return {invoice: {'attachment': attachment}}

    def _is_embedding_to_invoice_pdf_needed(self):
        self.ensure_one()
        if self.code != 'nlcius_1':
            return super()._is_embedding_to_invoice_pdf_needed()
        return False  # ubl must not be embedded to PDF.

    def _create_invoice_from_xml_tree(self, filename, tree):
        self.ensure_one()
        if self._is_nlcius(filename, tree):
            return self._decode_en_16931(tree, self.env['account.move'])
        return super()._create_invoice_from_xml_tree(filename, tree)

    def _update_invoice_from_xml_tree(self, filename, tree, invoice):
        self.ensure_one()
        if self._is_nlcius(filename, tree):
            return self._decode_en_16931(tree, invoice)
        return super()._update_invoice_from_xml_tree(filename, tree, invoice)

    ####################################################
    # Account_edi_ubl override
    ####################################################
    def _get_ubl_partner_values(self, partner):
        # OVERRIDE
        values = super()._get_ubl_partner_values(partner)
        endpoint = partner.l10n_nl_oin or partner.l10n_nl_kvk
        if partner.country_code == 'NL' and endpoint:
            scheme = '0190' if partner.l10n_nl_oin else '0106'
            values['en_16931_endpoint'] = endpoint
            values['en_16931_endpoint_scheme'] = scheme
            values['legal_entity'] = endpoint
            values['legal_entity_scheme'] = scheme
            values['partner_identification'] = endpoint

        return values

    def _get_ubl_values(self, invoice):
        values = super()._get_ubl_values(invoice)
        if self.code != 'nlcius_1':
            return values

        values['customization_id'] = 'urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0'
        values['payment_means_code'] = 30
        return values

    ####################################################
    # Import
    ####################################################

    def _is_nlcius(self, filename, tree):
        if self.code != 'nlcius_1':
            return False
        customization_id = self._find_value("//*[local-name()='CustomizationID']", tree)
        return 'nlcius' in customization_id

    def _decode_en_16931(self, tree, invoice):
        res = super()._decode_en_16931(tree, invoice)
        if self.code != 'nlcius_1':
            return res

        if not res.partner_id:
            namespaces = self._get_ubl_namespaces(tree)
            endpoint = tree.xpath('//cac:AccountingSupplierParty/cac:Party//cbc:EndpointID', namespaces=namespaces)
            if endpoint:
                endpoint = endpoint[0]
                scheme = endpoint.attrib['schemeID']
                domains = []
                if scheme == '0106' and endpoint.text:
                    domains.append([('l10n_nl_kvk', '=', endpoint.text)])
                elif scheme == '0190' and endpoint.text:
                    domains.append([('l10n_nl_oin', '=', endpoint.text)])
                if domains:
                    partner = self.env['res.partner'].search(expression.OR(domains), limit=1)
                    if partner:
                        res.partner_id = partner
        return res

    ####################################################
    # Export
    ####################################################

    def _check_move_configuration(self, invoice):
        res = super()._check_move_configuration(invoice)
        if self.code != 'nlcius_1':
            return res

        errors = self._check_en_16931_invoice_configuration(invoice)

        supplier = invoice.company_id.partner_id.commercial_partner_id
        if not supplier.street or not supplier.zip or not supplier.city:
            errors.append(_("The supplier's address must include street, zip and city."))
        if supplier.country_code == 'NL' and not supplier.l10n_nl_kvk and not supplier.l10n_nl_oin:
            errors.append(_("The supplier must have a KvK-nummer or OIN."))

        customer = invoice.commercial_partner_id
        if customer.country_code == 'NL' and (not customer.street or not customer.zip or not customer.city):
            errors.append(_("Customer's address must include street, zip and city."))
        if customer.country_code == 'NL' and not customer.l10n_nl_kvk and not customer.l10n_nl_oin:
            errors.append(_("The customer must have a KvK-nummer or OIN."))

        if not invoice.partner_bank_id:
            errors.append(_("The supplier must have a bank account."))

        return errors

    def _export_nlcius(self, invoice):
        self.ensure_one()
        # Create file content.
        xml_content = b"<?xml version='1.0' encoding='UTF-8'?>"
        xml_content += self.env.ref('l10n_nl_edi.export_en_16931_invoice')._render(self._get_ubl_values(invoice))
        vat = invoice.company_id.partner_id.commercial_partner_id.vat
        xml_name = 'nlcius-%s%s%s.xml' % (vat or '', '-' if vat else '', invoice.name.replace('/', '_'))
        return self.env['ir.attachment'].create({
            'name': xml_name,
            'datas': base64.encodebytes(xml_content),
            'res_model': 'account.move',
            'res_id': invoice._origin.id,
            'mimetype': 'application/xml'
        })
