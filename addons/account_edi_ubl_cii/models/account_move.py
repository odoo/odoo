import binascii

from collections import defaultdict

from base64 import b64decode
from contextlib import contextmanager, suppress
from lxml import etree

from odoo.exceptions import UserError

from odoo import _, api, fields, models, Command


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

    def action_group_ungroup_lines_by_tax(self):
        """
        This action allows the user to reload an xml imported move, grouping or not lines by tax
        """
        self.ensure_one()
        self._check_move_for_group_ungroup_lines_by_tax()

        # Check if lines looks like they're grouped
        tax_ids = [str(line.tax_ids.ids) for line in self.line_ids if line.tax_ids]
        lines_grouped = len(set(tax_ids)) == len(tax_ids)

        old_amount_untaxed, old_amount_total = self.amount_untaxed, self.amount_total

        if lines_grouped:
            # if lines are grouped, we search the original xml and load it
            attachments = self.env['ir.attachment'].search(
                [
                    ('res_model', '=', 'account.move'),
                    ('res_id', '=', self.id),
                ],
                order='create_date',
            )
            if not attachments:
                raise UserError(_("Cannot find the origin XML, try by importing it again"))

            success = False
            for attachment in attachments:
                file_data = attachment._unwrap_edi_attachments()
                if file_data[0].get('xml_tree') is None:
                    continue
                ubl_cii_xml_builder = self._get_ubl_cii_builder_from_xml_tree(file_data[0]['xml_tree'])
                if ubl_cii_xml_builder is None:
                    continue
                self.invoice_line_ids = False
                with self._deactivate_extract_single_line_per_tax():
                    res = ubl_cii_xml_builder._import_invoice_ubl_cii(self, file_data[0])
                if res and self.amount_untaxed == old_amount_untaxed and self.amount_total == old_amount_total:
                    success = True
                    self._message_log(body=_("Ungrouped lines from %s", attachment['name']))
                    break
            if not success:
                raise UserError(_("Cannot find the origin XML, try by importing it again"))
        else:
            # if lines are not grouped, we group them based on the lines we have in the model
            line_vals = self._get_lines_vals_group_by_tax(self.invoice_line_ids, self.partner_id, fields.Date.to_string(self.date), self.currency_id)
            self.invoice_line_ids = False
            self.write({
                'invoice_line_ids': [Command.create(line) for line in line_vals]
            })
            if self.amount_untaxed != old_amount_untaxed or self.amount_total != old_amount_total:
                raise UserError(_("Cannot find the origin XML, try by importing it again"))
            self._message_log(body=_("Grouped lines by taxes"))

    def _check_move_for_group_ungroup_lines_by_tax(self):
        if self.state != 'draft':
            raise UserError(_("You can only (un)group lines of a draft invoice"))

    @api.model
    def _get_lines_vals_group_by_tax(self, lines_vals, partner_id, date, currency):
        """
        This method group the lines in lines_vals by tax.
        lines_vals can either be a list of vals dict(s) to create lines or account.move.line record(s)
        :param lines_vals: list of dict or account.move.line records
        :param partner_id: the partner of the move related to the lines
        :param date: the date of the move in str format
        :param currency: the currency of the move related to lines
        :return: a list of dict vals line grouped by tax
        """
        def _get_attr(line, attr, default):
            # Line is a record or a dict
            if attr in line:
                return line[attr]
            return default
        # squash amls with same tax id into one aml, with the total amount
        taxes = dict()  # store taxes refs to not browse on it each iteration
        line_vals_to_squash = defaultdict(list)
        for line in lines_vals:
            if currency.is_zero(_get_attr(line, 'price_unit', 0.0)):
                continue
            line_tax_ids = _get_attr(line, 'tax_ids', False)
            is_record = not isinstance(line_tax_ids, list)

            if not line_tax_ids:
                tax_ref = '[]'
            elif is_record:
                tax_ref = str(line_tax_ids.ids)
            elif all(isinstance(tax_id, int) for tax_id in line_tax_ids):
                tax_ref = str(line_tax_ids)
            else:
                # unhandled scheme for tax_ids
                return lines_vals

            tax_ids = taxes.get(tax_ref)
            if tax_ids is None:
                tax_ids = taxes[tax_ref] = line_tax_ids or self.env['account.tax'] if is_record else self.env['account.tax'].browse(line_tax_ids)
            line_vals_to_squash[tax_ids].append(line)

        properties = ['name', 'product_id', 'price_unit', 'quantity', 'discount', 'tax_ids']

        res = [(lines[0] if isinstance(lines[0], dict) else lines[0].read(properties)[0]) if len(lines) == 1 else {
            'name': " - ".join([partner_id.name, date] + ([tax.description or tax.name for tax in tax_ids] or [_("Untaxed")])),
            'product_id': False,
            'price_unit': sum(
                _get_attr(line, 'price_unit', 0.0) * _get_attr(line, 'quantity', 0.0) - _get_attr(line, 'price_unit', 0.0) * _get_attr(line, 'quantity', 0.0) * _get_attr(line, 'discount', 0.0) / 100
                for line in lines
            ),
            'quantity': 1,
            # 'deferred_start_date': None,
            # 'deferred_end_date': None,
            'tax_ids': tax_ids.ids
        } for tax_ids, lines in line_vals_to_squash.items()]
        return res

    @contextmanager
    def _deactivate_extract_single_line_per_tax(self):
        old_value = self.company_id.extract_single_line_per_tax
        self.company_id.extract_single_line_per_tax = False
        yield
        self.company_id.extract_single_line_per_tax = old_value

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
        if customization_id is not None:
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
            and self.is_sale_document() \
            and ubl_cii_format in self.env['res.partner']._get_ubl_cii_formats()

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
