# -*- coding: utf-8 -*-

import markupsafe
from odoo.addons.account_edi_ubl_bis3.models.account_edi_format import COUNTRY_EAS

from odoo import models, _


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    ####################################################
    # Import
    ####################################################

    def _is_ubl(self, filename, tree):
        """ OVERRIDE so that the generic ubl parser does not parse BIS3 any longer.
        """
        is_ubl = super()._is_ubl(filename, tree)
        return is_ubl and not self._is_nlcius(filename, tree)

    def _is_nlcius(self, filename, tree):
        profile_id = tree.find('./{*}ProfileID')
        customization_id = tree.find('./{*}CustomizationID')
        return tree.tag == '{urn:oasis:names:specification:ubl:schema:xsd:Invoice-2}Invoice' and \
            profile_id is not None and 'peppol' in profile_id.text and \
            customization_id is not None and 'nlcius' in customization_id.text

    def _bis3_get_extra_partner_domains(self, tree):
        if self.code == 'nlcius_1':
            endpoint = tree.find('./{*}AccountingSupplierParty/{*}Party/{*}EndpointID')
            if endpoint is not None:
                scheme = endpoint.attrib['schemeID']
                if scheme == '0106' and endpoint.text:
                    return [('l10n_nl_kvk', '=', endpoint.text)]
                elif scheme == '0190' and endpoint.text:
                    return [('l10n_nl_oin', '=', endpoint.text)]
        return super()._bis3_get_extra_partner_domains(tree)

    ####################################################
    # Export
    ####################################################

    def _get_nlcius_values(self, invoice):
        values = super()._get_bis3_values(invoice)
        values.update({
            'customization_id': 'urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0',
            'payment_means_code': 30,
        })

        for partner_vals in (values['customer_vals'], values['supplier_vals']):
            partner = partner_vals['partner']
            endpoint = partner.l10n_nl_oin or partner.l10n_nl_kvk
            if partner.country_code == 'NL' and endpoint:
                scheme = '0190' if partner.l10n_nl_oin else '0106'
                partner_vals.update({
                    'bis3_endpoint': endpoint,
                    'bis3_endpoint_scheme': scheme,
                    'legal_entity': endpoint,
                    'legal_entity_scheme': scheme,
                    'partner_identification': endpoint,
                })

        return values

    def _export_nlcius(self, invoice):
        self.ensure_one()
        # Create file content.
        xml_content = markupsafe.Markup("<?xml version='1.0' encoding='UTF-8'?>")
        xml_content += self.env.ref('l10n_nl_edi.export_nlcius_invoice')._render(self._get_nlcius_values(invoice))
        vat = invoice.company_id.partner_id.commercial_partner_id.vat
        xml_name = 'nlcius-%s%s%s.xml' % (vat or '', '-' if vat else '', invoice.name.replace('/', '_'))
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
        if self.code != 'nlcius_1':
            return errors

        supplier = invoice.company_id.partner_id.commercial_partner_id
        if not supplier.street or not supplier.zip or not supplier.city:
            errors.append(_("The supplier's address must include street, zip and city (%s).", supplier.display_name))
        if supplier.country_code == 'NL' and not supplier.l10n_nl_kvk and not supplier.l10n_nl_oin:
            errors.append(_("The supplier %s must have a KvK-nummer or OIN.", supplier.display_name))
        if not supplier.vat:
            errors.append(_("Please define a VAT number for '%s'.", supplier.display_name))

        customer = invoice.commercial_partner_id
        if customer.country_code == 'NL' and (not customer.street or not customer.zip or not customer.city):
            errors.append(_("Customer's address must include street, zip and city (%s).", customer.display_name))
        if customer.country_code == 'NL' and not customer.l10n_nl_kvk and not customer.l10n_nl_oin:
            errors.append(_("The customer %s must have a KvK-nummer or OIN.", customer.display_name))

        if not invoice.partner_bank_id:
            errors.append(_("The supplier %s must have a bank account.", supplier.display_name))

        if invoice.invoice_line_ids.filtered(lambda l: not (l.product_id.name or l.name)):
            errors.append(_('Each invoice line must have a product or a label.'))

        if invoice.invoice_line_ids.tax_ids.invoice_repartition_line_ids.filtered(lambda r: r.use_in_tax_closing) and \
           not supplier.vat:
            errors.append(_("When vat is present, the supplier must have a vat number."))

        return errors

    def _is_compatible_with_journal(self, journal):
        self.ensure_one()
        if self.code != 'nlcius_1':
            return super()._is_compatible_with_journal(journal)
        return journal.type == 'sale' and journal.country_code == 'NL'

    def _post_invoice_edi(self, invoices):
        self.ensure_one()
        if self.code != 'nlcius_1':
            return super()._post_invoice_edi(invoices)

        invoice = invoices  # no batch ensure that there is only one invoice
        attachment = self._export_nlcius(invoice)
        return {invoice: {'success': True, 'attachment': attachment}}

    def _create_invoice_from_xml_tree(self, filename, tree):
        self.ensure_one()
        if self.code == 'nlcius_1' and self._is_nlcius(filename, tree):
            return self._decode_bis3(tree, self.env['account.move'])
        return super()._create_invoice_from_xml_tree(filename, tree)

    def _update_invoice_from_xml_tree(self, filename, tree, invoice):
        self.ensure_one()
        if self.code == 'nlcius_1' and self._is_nlcius(filename, tree):
            return self._decode_bis3(tree, invoice)
        return super()._update_invoice_from_xml_tree(filename, tree, invoice)

    def _is_required_for_invoice(self, invoice):
        self.ensure_one()
        if self.code != 'nlcius_1':
            return super()._is_required_for_invoice(invoice)

        return invoice.commercial_partner_id.country_code in COUNTRY_EAS
