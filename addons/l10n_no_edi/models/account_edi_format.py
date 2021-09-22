# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.addons.account_edi_ubl_bis3.models.account_edi_format import COUNTRY_EAS


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    ####################################################
    # Import
    ####################################################

    def _is_ubl(self, filename, tree):
        """ OVERRIDE so that the generic ubl parser does not parse BIS3 any longer.
        """
        is_ubl = super()._is_ubl(filename, tree)
        return is_ubl and not self._is_ehf_3(filename, tree)

    def _is_ehf_3(self, filename, tree):
        ns = self._get_bis3_namespaces()
        return tree.tag == '{urn:oasis:names:specification:ubl:schema:xsd:Invoice-2}Invoice' \
            and 'peppol' in tree.findtext('./cbc:ProfileID', '', namespaces=ns) \
            and tree.xpath(
                "./cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID[text()='Foretaksregisteret']",
                namespaces=ns) is not None

    def _bis3_get_extra_partner_domains(self, tree):
        if self.code == 'ehf_3':
            ns = self._get_bis3_namespaces()
            bronnoysund = tree.xpath('./cac:AccountingSupplierParty/cac:Party/cbc:EndpointID[@schemeID="0192"]/text()', namespaces=ns)
            if bronnoysund:
                return [('l10n_no_bronnoysund_number', '=', bronnoysund[0])]
        return super()._bis3_get_extra_partner_domains(tree)

    ####################################################
    # Export
    ####################################################

    def _get_ehf_3_values(self, invoice):
        values = super()._get_bis3_values(invoice)
        for partner_vals in (values['customer_vals'], values['supplier_vals']):
            partner = partner_vals['partner']
            if partner.country_code == 'NO':
                partner_vals.update(
                    bis3_endpoint=partner.l10n_no_bronnoysund_number,
                    bis3_endpoint_scheme='0192',
                )

        return values

    def _export_ehf_3(self, invoice):
        self.ensure_one()
        # Create file content.
        xml_content = self.env.ref('l10n_no_edi.export_ehf_3_invoice')._render(self._get_ehf_3_values(invoice))
        vat = invoice.company_id.partner_id.commercial_partner_id.vat
        xml_name = 'ehf-%s%s%s.xml' % (vat or '', '-' if vat else '', invoice.name.replace('/', '_'))
        return self.env['ir.attachment'].create({
            'name': xml_name,
            'raw': xml_content.encode(),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'mimetype': 'application/xml'
        })

    ####################################################
    # Account.edi.format override
    ####################################################

    def _check_move_configuration(self, invoice):
        errors = super()._check_move_configuration(invoice)
        if self.code != 'ehf_3':
            return errors

        supplier = invoice.company_id.partner_id.commercial_partner_id
        if supplier.country_code == 'NO' and not supplier.l10n_no_bronnoysund_number:
            errors.append(_("The supplier %r must have a Bronnoysund company registry.", supplier.display_name))

        if supplier.country_code != 'NO' and supplier.country_code not in COUNTRY_EAS:
            errors.append(_("The supplier %r is from a country that is not supported for EHF (Bis3)", supplier.display_name))

        customer = invoice.commercial_partner_id
        if customer.country_code == 'NO' and not customer.l10n_no_bronnoysund_number:
            errors.append(_("The customer %r must have a Bronnoysund company registry.", customer.display_name))

        if customer.country_code != 'NO' and customer.country_code not in COUNTRY_EAS:
            errors.append(_("The customer %r is from a country that is not supported for EHF (Bis3)", customer.display_name))

        return errors

    def _is_compatible_with_journal(self, journal):
        self.ensure_one()
        if self.code != 'ehf_3':
            return super()._is_compatible_with_journal(journal)
        return journal.type == 'sale' and journal.country_code == 'NO'

    def _post_invoice_edi(self, invoices):
        self.ensure_one()
        if self.code != 'ehf_3':
            return super()._post_invoice_edi(invoices)

        invoice = invoices  # no batch ensure that there is only one invoice
        attachment = self._export_ehf_3(invoice)
        return {invoice: {'attachment': attachment}}

    def _create_invoice_from_xml_tree(self, filename, tree):
        self.ensure_one()
        if self.code == 'ehf_3' and self._is_ehf_3(filename, tree):
            return self._decode_bis3(tree, self.env['account.move'])
        return super()._create_invoice_from_xml_tree(filename, tree)

    def _update_invoice_from_xml_tree(self, filename, tree, invoice):
        self.ensure_one()
        if self.code == 'ehf_3' and self._is_ehf_3(filename, tree):
            return self._decode_bis3(tree, invoice)
        return super()._update_invoice_from_xml_tree(filename, tree, invoice)
