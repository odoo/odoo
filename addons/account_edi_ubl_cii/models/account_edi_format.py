# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _
from odoo.addons.account_edi_ubl_cii.models.account_edi_common import COUNTRY_EAS
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)

FORMAT_CODES = [
    'facturx_1_0_05',
    'ubl_bis3',
    'ubl_de',
    'nlcius_1',
    'efff_1',
    'ubl_2_1',
    'ubl_a_nz',
    'ubl_sg',
]

class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    ####################################################
    # Helpers
    ####################################################

    def _infer_xml_builder_from_tree(self, tree):
        self.ensure_one()
        ubl_version = tree.find('{*}UBLVersionID')
        customization_id = tree.find('{*}CustomizationID')
        if tree.tag == '{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}CrossIndustryInvoice':
            return self.env['account.edi.xml.cii']
        if ubl_version is not None:
            if ubl_version.text == '2.0':
                return self.env['account.edi.xml.ubl_20']
            if ubl_version.text == '2.1':
                return self.env['account.edi.xml.ubl_21']
        if customization_id is not None:
            if 'xrechnung' in customization_id.text:
                return self.env['account.edi.xml.ubl_de']
            if customization_id.text == 'urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0':
                return self.env['account.edi.xml.ubl_nl']
            if customization_id.text == 'urn:cen.eu:en16931:2017#conformant#urn:fdc:peppol.eu:2017:poacc:billing:international:aunz:3.0':
                return self.env['account.edi.xml.ubl_a_nz']
            if customization_id.text == 'urn:cen.eu:en16931:2017#conformant#urn:fdc:peppol.eu:2017:poacc:billing:international:sg:3.0':
                return self.env['account.edi.xml.ubl_sg']
            # Allow to parse any format derived from the european semantic norm EN16931
            if 'urn:cen.eu:en16931:2017' in customization_id.text:
                return self.env['account.edi.xml.ubl_bis3']
        return

    def _get_xml_builder(self, company):
        # see https://communaute.chorus-pro.gouv.fr/wp-content/uploads/2017/08/20170630_Solution-portail_Dossier_Specifications_Fournisseurs_Chorus_Facture_V.1.pdf
        # page 45 -> ubl 2.1 for France seems also supported
        # Only show the Factur-X option for DE and FR companies. When generating the PDF, add a Factur-X xml if there
        # isn't an existing one. So there's always a Factur-X in the PDF, even without the option.
        if self.code == 'facturx_1_0_05' and company.country_id.code in ['DE', 'FR']:
            return self.env['account.edi.xml.cii']
        # if the company's country is not in the EAS mapping, nothing is generated
        # 'NO' has to be present in COUNTRY_EAS
        if self.code == 'ubl_bis3' and company.country_id.code in COUNTRY_EAS:
            return self.env['account.edi.xml.ubl_bis3']
        # the EDI option will only appear on the journal of dutch companies
        if self.code == 'nlcius_1' and company.country_id.code == 'NL':
            return self.env['account.edi.xml.ubl_nl']
        # the EDI option will only appear on the journal of german companies
        if self.code == 'ubl_de' and company.country_id.code == 'DE':
            return self.env['account.edi.xml.ubl_de']
        if self.code == 'efff_1' and company.country_id.code == 'BE':
            return self.env['account.edi.xml.ubl_efff']
        if self.code == 'ubl_a_nz' and company.country_id.code in ['AU', 'NZ']:
            return self.env['account.edi.xml.ubl_a_nz']
        if self.code == 'ubl_sg' and company.country_id.code == 'SG':
            return self.env['account.edi.xml.ubl_sg']

    def _is_ubl_cii_available(self, company):
        """
        Returns a boolean indicating whether it is possible to generate an xml file using one of the formats from this
        module or not
        """
        return self._get_xml_builder(company) is not None

    ####################################################
    # Export: Account.edi.format override
    ####################################################

    def _is_compatible_with_journal(self, journal):
        # EXTENDS account_edi
        # the formats appear on the journal only if they are compatible (e.g. NLCIUS only appear for dutch companies)
        self.ensure_one()
        if self.code not in FORMAT_CODES:
            return super()._is_compatible_with_journal(journal)
        return self._is_ubl_cii_available(journal.company_id) and journal.type == 'sale'

    def _is_enabled_by_default_on_journal(self, journal):
        # EXTENDS account_edi
        self.ensure_one()
        if self.code not in FORMAT_CODES:
            return super()._is_enabled_by_default_on_journal(journal)
        return False

    def _ubl_cii_post_invoice(self, invoice):
        # EXTENDS account_edi
        self.ensure_one()

        builder = self._get_xml_builder(invoice.company_id)
        # For now, the errors are not displayed anywhere, don't want to annoy the user
        xml_content, errors = builder._export_invoice(invoice)

        # DEBUG: send directly to the test platform (the one used by ecosio)
        #response = self.env['account.edi.common']._check_xml_ecosio(invoice, xml_content, builder._export_invoice_ecosio_schematrons())

        attachment_create_vals = {
            'name': builder._export_invoice_filename(invoice),
            'raw': xml_content,
            'mimetype': 'application/xml',
        }
        # we don't want the Factur-X and E-FFF xml to appear in the attachment of the invoice when confirming it
        # E-FFF will appear after the pdf is generated, Factur-X will never appear (it's contained in the PDF)
        if self.code not in ['facturx_1_0_05', 'efff_1']:
            attachment_create_vals.update({'res_id': invoice.id, 'res_model': 'account.move'})

        attachment = self.env['ir.attachment'].create(attachment_create_vals)

        res = {invoice: {'attachment': attachment}}
        if errors and self.code == 'facturx_1_0_05':
            res[invoice].update({
                'success': False,
                'error': _("Errors occured while creating the EDI document (format: %s). The receiver "
                           "might refuse it.", builder._description)
                         + '<p> <li>' + "</li> <li>".join(errors) + '</li> </p>',
                'blocking_level': 'info',
            })
        else:
            res[invoice]['success'] = True
        return res

    def _get_move_applicability(self, move):
        # EXTENDS account_edi
        self.ensure_one()
        if self.code not in FORMAT_CODES:
            return super()._get_move_applicability(move)

        if self._is_ubl_cii_available(move.company_id) and move.move_type in ('out_invoice', 'out_refund'):
            return {'post': self._ubl_cii_post_invoice}

    def _is_embedding_to_invoice_pdf_needed(self):
        # EXTENDS account_edi
        self.ensure_one()

        if self.code == 'facturx_1_0_05':
            return True
        return super()._is_embedding_to_invoice_pdf_needed()

    def _prepare_invoice_report(self, pdf_writer, edi_document):
        # EXTENDS account_edi
        self.ensure_one()
        if self.code != 'facturx_1_0_05':
            return super()._prepare_invoice_report(pdf_writer, edi_document)
        attachment = edi_document.sudo().attachment_id
        if not attachment:
            return

        pdf_writer.embed_odoo_attachment(attachment, subtype='text/xml')
        if not pdf_writer.is_pdfa:
            try:
                pdf_writer.convert_to_pdfa()
            except Exception as e:
                _logger.exception("Error while converting to PDF/A: %s", e)
            metadata_template = self.env.ref('account_edi_ubl_cii.account_invoice_pdfa_3_facturx_metadata',
                                             raise_if_not_found=False)
            if metadata_template:
                content = self.env['ir.qweb']._render('account_edi_ubl_cii.account_invoice_pdfa_3_facturx_metadata', {
                    'title': edi_document.move_id.name,
                    'date': fields.Date.context_today(self),
                })
                pdf_writer.add_file_metadata(content.encode())

    ####################################################
    # Import: Account.edi.format override
    ####################################################

    def _create_invoice_from_xml_tree(self, filename, tree, journal=None):
        # EXTENDS account_edi
        self.ensure_one()

        if not journal:
            journal = self.env['account.journal'].browse(self._context.get("default_journal_id"))
        if not journal:
            context_move_type = self._context.get("default_move_type", "entry")
            if context_move_type in self.env['account.move'].get_sale_types():
                journal_type = "sale"
            elif context_move_type in self.env['account.move'].get_purchase_types():
                journal_type = "purchase"
            else:
                raise UserError(_("The journal in which to upload should either be a sale or a purchase journal."))
            journal = self.env['account.journal'].search([
                ('company_id', '=', self.env.company.id), ('type', '=', journal_type)
            ], limit=1)

        if not self._is_ubl_cii_available(journal.company_id) and self.code != 'facturx_1_0_05':
            return super()._create_invoice_from_xml_tree(filename, tree, journal=journal)

        # infer the xml builder
        invoice_xml_builder = self._infer_xml_builder_from_tree(tree)

        if invoice_xml_builder is not None:
            invoice = invoice_xml_builder._import_invoice(journal, filename, tree)
            if invoice:
                return invoice

        return super()._create_invoice_from_xml_tree(filename, tree, journal=journal)

    def _update_invoice_from_xml_tree(self, filename, tree, invoice):
        # EXTENDS account_edi
        self.ensure_one()

        if not self._is_ubl_cii_available(invoice.company_id) and self.code != 'facturx_1_0_05':
            return super()._update_invoice_from_xml_tree(filename, tree, invoice)

        # infer the xml builder
        invoice_xml_builder = self._infer_xml_builder_from_tree(tree)

        if invoice_xml_builder is not None:
            invoice = invoice_xml_builder._import_invoice(invoice.journal_id, filename, tree, invoice)
            if invoice:
                return invoice

        return super()._update_invoice_from_xml_tree(filename, tree, invoice)
