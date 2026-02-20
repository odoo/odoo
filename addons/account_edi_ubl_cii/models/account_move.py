<<<<<<< e1e6fcb3aa4b46b0b6ce65a93826e4c9e43161a7
import binascii

from base64 import b64decode
from contextlib import suppress
from lxml import etree

from odoo import _, api, fields, models, Command
||||||| 159fb4168be9e8bd16d7b173d014c0665988f111
# -*- coding: utf-8 -*-
from odoo import api, fields, models
=======
# -*- coding: utf-8 -*-
import re

from odoo import _, api, fields, models, Command
from odoo.exceptions import UserError
>>>>>>> af784b928cacda52ed32c55279ad87f42e69e3ab


class AccountMove(models.Model):
    _inherit = 'account.move'

    ubl_cii_xml_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="Attachment",
        compute=lambda self: self._compute_linked_attachment_id('ubl_cii_xml_id', 'ubl_cii_xml_file'),
        depends=['ubl_cii_xml_file']
    )
    ubl_cii_xml_file = fields.Binary(
        attachment=True,
        string="UBL/CII File",
        copy=False,
    )

    # -------------------------------------------------------------------------
<<<<<<< e1e6fcb3aa4b46b0b6ce65a93826e4c9e43161a7
    # ACTIONS
    # -------------------------------------------------------------------------

    def action_invoice_download_ubl(self):
        if invoices_with_ubl := self.filtered('ubl_cii_xml_id'):
            return {
                'type': 'ir.actions.act_url',
                'url': f'/account/download_invoice_documents/{",".join(map(str, invoices_with_ubl.ids))}/ubl',
                'target': 'download',
            }
        return False

    # -------------------------------------------------------------------------
    # BUSINESS
    # -------------------------------------------------------------------------

    def _get_fields_to_detach(self):
        # EXTENDS account
        fields_list = super()._get_fields_to_detach()
        fields_list.append("ubl_cii_xml_file")
        return fields_list

    def _get_invoice_legal_documents(self, filetype, allow_fallback=False):
        # EXTENDS account
        if filetype == 'ubl':
            if ubl_attachment := self.ubl_cii_xml_id:
                return {
                    'filename': ubl_attachment.name,
                    'filetype': 'xml',
                    'content': ubl_attachment.raw,
                }
        return super()._get_invoice_legal_documents(filetype, allow_fallback=allow_fallback)

    def get_extra_print_items(self):
        print_items = super().get_extra_print_items()
        if self.ubl_cii_xml_id:
            print_items.append({
                'key': 'download_ubl',
                'description': _('XML UBL'),
                **self.action_invoice_download_ubl(),
            })
        return print_items

    # -------------------------------------------------------------------------
||||||| 159fb4168be9e8bd16d7b173d014c0665988f111
=======
    # ACTIONS
    # -------------------------------------------------------------------------
    def action_group_ungroup_lines_by_tax(self):
        """
        This action allows the user to reload an imported move, grouping or not lines by tax
        """
        self.ensure_one()
        self._check_move_for_group_ungroup_lines_by_tax()

        # Check if lines look like they're grouped
        lines_grouped = any(
            re.match(re.escape(self.partner_id.name or _("Unknown partner")) + r' - \d+ - .*', line.name)
            for line in self.line_ids.filtered(lambda x: x.display_type == 'product')
        )

        if lines_grouped:
            self._ungroup_lines()
        else:
            self._group_lines_by_tax()

    def _ungroup_lines(self):
        """
        Ungroup lines using the original file, used to import the move
        """
        error_message = _("Cannot find the origin file, try by importing it again")
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', self.id),
        ], order='create_date')
        if not attachments:
            raise UserError(error_message)

        success = False
        for file_data in attachments._unwrap_edi_attachments():
            if file_data.get('xml_tree') is None:
                continue
            ubl_cii_xml_builder = self._get_ubl_cii_builder_from_xml_tree(file_data['xml_tree'])
            if ubl_cii_xml_builder is None:
                continue
            self.invoice_line_ids = [Command.clear()]
            res = ubl_cii_xml_builder._import_invoice_ubl_cii(self, file_data)
            if res:
                success = True
                self._message_log(body=_("Ungrouped lines from %s", file_data['attachment'].name))
                break
        if not success:
            raise UserError(error_message)

    def _group_lines_by_tax(self):
        """
        Group lines by tax, based on the invoice lines
        """
        line_vals = self._get_line_vals_group_by_tax(self.partner_id, fields.Date.to_string(self.date))
        self.invoice_line_ids = [Command.clear()]
        self.invoice_line_ids = line_vals
        self._message_log(body=_("Grouped lines by tax"))

    def _get_line_vals_group_by_tax(self, partner, date):
        """
        Create a collection of dicts containing the values to create invoice lines, grouped by
        tax and deferred date if present.
        :param partner: partner linked to the move
        :param date: date of the move (string format)
        """
        base_lines = [
            line._convert_to_tax_base_line_dict()
            for line in self.line_ids.filtered(lambda x: x.display_type == 'product')
        ]

        to_process = []
        for base_line in base_lines:
            to_update_vals, tax_values_list = self.env['account.tax']._compute_taxes_for_single_line(base_line)
            to_process.append((base_line, to_update_vals, tax_values_list))

        deferred = 'deferred_start_date' in self.env['account.move.line']._fields  # enterprise field

        def grouping_key_generator(base_line, tax_values):
            dates = (False, False)
            record = base_line['record']
            if deferred:
                dates = (record.deferred_start_date, record.deferred_end_date)
            return {'tax': (record.tax_ids, record.account_id, dates)}

        aggregated_lines = self.env['account.tax'].with_company(self.company_id)._aggregate_taxes(to_process, grouping_key_generator=grouping_key_generator)

        to_create = []
        for tax_detail in aggregated_lines['tax_details'].values():
            taxes, account, (deferred_start_date, deferred_end_date) = tax_detail['tax']
            vals = {
                'name': " - ".join([partner.name or _("Unknown partner"), account.code, " / ".join([tax.name for tax in taxes]) or _("Untaxed")]),
                'quantity': 1,
                'price_unit': tax_detail['base_amount_currency'],
                'tax_ids': [Command.link(tax.id) for tax in taxes],
                'account_id': account.id,
            }
            if deferred:
                vals.update({'deferred_start_date': deferred_start_date, 'deferred_end_date': deferred_end_date})
            to_create.append(Command.create(vals))

        return to_create

    def _check_move_for_group_ungroup_lines_by_tax(self):
        """
        Perform checks to evaluate if a move is eligible to grouping/ungrouping
        """
        if not self.is_purchase_document(include_receipts=True):
            raise UserError(_("You can only (un)group lines of a incoming invoice (vendor bill)"))
        if self.state != 'draft':
            raise UserError(_("You can only (un)group lines of a draft invoice"))
        # TO REMOVE IN 18.0+ as purchase_edi_ubl_bis module is created
        if 'purchase_order_id' in self.env['account.move.line']._fields:  # purchase field
            if any(line.purchase_order_id for line in self.line_ids):
                raise UserError(_("You can only (un)group lines of an invoice not linked to a purchase order"))

    # -------------------------------------------------------------------------
>>>>>>> af784b928cacda52ed32c55279ad87f42e69e3ab
    # EDI
    # -------------------------------------------------------------------------

    @api.model
    def _get_ubl_cii_builder_from_xml_tree(self, tree):
        customization_id = tree.find('{*}CustomizationID')
        if tree.tag == '{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}CrossIndustryInvoice':
            return self.env['account.edi.xml.cii']
        ubl_version = tree.find('{*}UBLVersionID')
        if ubl_version is not None:
            if ubl_version.text == '2.0':
                return self.env['account.edi.xml.ubl_20']
            if ubl_version.text in ('2.1', '2.2', '2.3'):
                return self.env['account.edi.xml.ubl_21']
        if customization_id is not None and customization_id.text:
            if 'xrechnung' in customization_id.text:
                return self.env['account.edi.xml.ubl_de']
            if customization_id.text == 'urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0':
                return self.env['account.edi.xml.ubl_nl']
            if customization_id.text == 'urn:cen.eu:en16931:2017#conformant#urn:fdc:peppol.eu:2017:poacc:billing:international:aunz:3.0':
                return self.env['account.edi.xml.ubl_a_nz']
            if customization_id.text == 'urn:cen.eu:en16931:2017#conformant#urn:fdc:peppol.eu:2017:poacc:billing:international:sg:3.0':
                return self.env['account.edi.xml.ubl_sg']
            if 'urn:cen.eu:en16931:2017' in customization_id.text:
                return self.env['account.edi.xml.ubl_bis3']

    @api.model
    def _ubl_parse_attached_document(self, tree):
        """
        In UBL, an AttachedDocument file is a wrapper around multiple different UBL files.
        According to the specifications the original document is stored within the top most
        Attachment node either as an Attachment/EmbeddedDocumentBinaryObject or (in special cases)
        a CDATA string stored in Attachment/ExternalReference/Description.

        We must parse this before passing the original file to the decoder to figure out how best
        to handle it.
        """
        attachment_node = tree.find('{*}Attachment')
        if attachment_node is None:
            return tree

        attachment_binary_data = attachment_node.find('./{*}EmbeddedDocumentBinaryObject')
        if attachment_binary_data is not None \
                and attachment_binary_data.attrib.get('mimeCode') in ('application/xml', 'text/xml'):
            with suppress(etree.XMLSyntaxError, binascii.Error):
                text = b64decode(attachment_binary_data.text)
                return etree.fromstring(text)

        external_reference = attachment_node.find('./{*}ExternalReference')
        if external_reference is not None:
            description = external_reference.findtext('./{*}Description')
            mime_code = external_reference.findtext('./{*}MimeCode')

            if description and mime_code in ('application/xml', 'text/xml'):
                with suppress(etree.XMLSyntaxError):
                    return etree.fromstring(description.encode('utf-8'))
        return tree

    def _get_edi_decoder(self, file_data, new=False):
        # EXTENDS 'account'
        if file_data['type'] == 'xml':
            if etree.QName(file_data['xml_tree']).localname == 'AttachedDocument':
                file_data['xml_tree'] = self._ubl_parse_attached_document(file_data['xml_tree'])
            ubl_cii_xml_builder = self._get_ubl_cii_builder_from_xml_tree(file_data['xml_tree'])
            if ubl_cii_xml_builder is not None:
                return ubl_cii_xml_builder._import_invoice_ubl_cii

        return super()._get_edi_decoder(file_data, new=new)

    def _need_ubl_cii_xml(self, ubl_cii_format):
        self.ensure_one()
        return not self.ubl_cii_xml_id \
            and (self.is_sale_document() or self._is_exportable_as_self_invoice()) \
            and ubl_cii_format in self.env['res.partner']._get_ubl_cii_formats()

    def _is_exportable_as_self_invoice(self):
        # To override in account_peppol_selfbilling
        return False

    @api.model
    def _get_line_vals_list(self, lines_vals):
        """ Get invoice line values list.

        param list line_vals: List of values [name, qty, price, tax].
        :return: List of invoice line values.
        """
        return [{
            'sequence': 0,  # be sure to put these lines above the 'real' invoice lines
            'name': name,
            'quantity': quantity,
            'price_unit': price_unit,
            'tax_ids': [Command.set(tax_ids)],
        } for name, quantity, price_unit, tax_ids in lines_vals]

    def _get_specific_tax(self, name, amount_type, amount, tax_type):
        AccountMoveLine = self.env['account.move.line']
        if hasattr(AccountMoveLine, '_predict_specific_tax'):
            # company check is already done in the prediction query
            predicted_tax_id = AccountMoveLine._predict_specific_tax(
                self, name, self.partner_id, amount_type, amount, tax_type,
            )
            return self.env['account.tax'].browse(predicted_tax_id)
        return self.env['account.tax']
