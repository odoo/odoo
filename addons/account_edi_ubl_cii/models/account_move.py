from contextlib import suppress
from base64 import b64decode
import binascii
from lxml import etree
from collections import defaultdict

from odoo import _, api, fields, models, Command
from odoo.exceptions import UserError
from odoo.tools.mimetypes import guess_mimetype


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
        return {
            'type': 'ir.actions.act_url',
            'url': f'/account/download_invoice_documents/{",".join(map(str, self.ids))}/ubl?allow_fallback=true',
            'target': 'download',
        }

    def action_group_ungroup_lines_by_tax(self):
        """
        This action allows the user to reload an imported move, grouping or not lines by tax
        """
        self.ensure_one()
        self._check_move_for_group_ungroup_lines_by_tax()

        # Check if lines looks like they're grouped
        tax_ids = [str(line.tax_ids.ids) for line in self.line_ids if line.tax_ids]
        lines_grouped = len(set(tax_ids)) == len(tax_ids)

        old_amount_untaxed, old_amount_total = self.amount_untaxed, self.amount_total

        attachments = self.env['ir.attachment'].search(
            [
                ('res_model', '=', 'account.move'),
                ('res_id', '=', self.id),
            ],
            order='create_date',
        )
        if not attachments:
            raise UserError(_("Cannot find the origin XML, try by importing it again"))

        files_data = self._to_files_data(attachments)
        files_data.extend(self._unwrap_attachments(files_data))

        file_data_groups = self._group_files_data_into_groups_of_mixed_types(files_data)

        success = False
        for file_data_group in file_data_groups:
            self.invoice_line_ids = [Command.clear()]
            self.with_context(ungroup_invoice_lines=lines_grouped, group_invoice_lines=not lines_grouped)._extend_with_attachments(file_data_group)
            if self.amount_untaxed == old_amount_untaxed and self.amount_total == old_amount_total:
                success = True
                self._message_log(body=_("Ungrouped lines from origin file") if lines_grouped else _("Grouped lines by tax"))
                break

        if not success:
            raise UserError(_("Cannot find the origin XML, try by importing it again"))

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

        res = [{
            'name': " - ".join([partner_id.name, date] + ([tax.name for tax in tax_ids] or [_("Untaxed")])),
            'price_unit': sum(
                _get_attr(line, 'price_unit', 0.0) * _get_attr(line, 'quantity', 0.0) - _get_attr(line, 'price_unit', 0.0) * _get_attr(line, 'quantity', 0.0) * _get_attr(line, 'discount', 0.0) / 100
                for line in lines
            ),
            'quantity': 1,
            'tax_ids': tax_ids.ids
        } for tax_ids, lines in line_vals_to_squash.items()]
        return res

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
        self.ensure_one()
        if filetype == 'ubl':
            if ubl_attachment := self.ubl_cii_xml_id:
                return {
                    'filename': ubl_attachment.name,
                    'filetype': 'xml',
                    'content': ubl_attachment.raw,
                }
            elif allow_fallback:
                if self.partner_id and (suggested_edi_format := self.commercial_partner_id._get_suggested_ubl_cii_edi_format()):
                    builder = self.env['res.partner']._get_edi_builder(suggested_edi_format)
                    xml_content, errors = builder._export_invoice(self)
                    filename = builder._export_invoice_filename(self)
                    return {
                        'filename': filename,
                        'filetype': 'xml',
                        'content': xml_content,
                        'errors': errors,
                    }
        return super()._get_invoice_legal_documents(filetype, allow_fallback=allow_fallback)

    def get_extra_print_items(self):
        print_items = super().get_extra_print_items()
        posted_moves = self.filtered(lambda move: move.state == 'posted')
        suggested_edi_formats = {
            suggested_format
            for partner in posted_moves.commercial_partner_id
            if (suggested_format := partner ._get_suggested_ubl_cii_edi_format())
        }
        if posted_moves.ubl_cii_xml_id or suggested_edi_formats:
            print_items.append({
                'key': 'download_ubl',
                'description': _('Export XML'),
                **posted_moves.action_invoice_download_ubl(),
            })
        return print_items

    # -------------------------------------------------------------------------
    # EDI
    # -------------------------------------------------------------------------

    def _get_import_file_type(self, file_data):
        """ Identify UBL files. """
        # EXTENDS 'account'
        if (tree := file_data['xml_tree']) is not None:
            if etree.QName(tree).localname == 'AttachedDocument':
                return 'account.edi.xml.ubl.attached_document'
            if tree.tag == '{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}CrossIndustryInvoice':
                return 'account.edi.xml.cii'
            if ubl_version := tree.findtext('{*}UBLVersionID'):
                if ubl_version == '2.0':
                    return 'account.edi.xml.ubl_20'
                if ubl_version in ('2.1', '2.2', '2.3'):
                    return 'account.edi.xml.ubl_21'
            if customization_id := tree.findtext('{*}CustomizationID'):
                if 'xrechnung' in customization_id:
                    return 'account.edi.xml.ubl_de'
                if customization_id == 'urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0':
                    return 'account.edi.xml.ubl_nl'
                if customization_id == 'urn:cen.eu:en16931:2017#conformant#urn:fdc:peppol.eu:2017:poacc:billing:international:aunz:3.0':
                    return 'account.edi.xml.ubl_a_nz'
                if customization_id == 'urn:cen.eu:en16931:2017#conformant#urn:fdc:peppol.eu:2017:poacc:billing:international:sg:3.0':
                    return 'account.edi.xml.ubl_sg'
                if 'urn:cen.eu:en16931:2017' in customization_id:
                    return 'account.edi.xml.ubl_bis3'

        return super()._get_import_file_type(file_data)

    def _unwrap_attachment(self, file_data, recurse=True):
        """ Unwrap UBL AttachedDocument files, which are wrappers around an inner file. """

        if file_data['import_file_type'] != 'account.edi.xml.ubl.attached_document':
            return super()._unwrap_attachment(file_data, recurse)

        content, tree = self._ubl_parse_attached_document(file_data['xml_tree'])
        if not content:
            return []

        embedded_file_data = {
            'name': file_data['name'],
            'raw': content,
            'xml_tree': tree,
            'mimetype': guess_mimetype(content),
            'attachment': None,
            'origin_attachment': file_data['origin_attachment'],
            'origin_import_file_type': file_data['origin_import_file_type'],
        }
        embedded_file_data['import_file_type'] = self._get_import_file_type(embedded_file_data)

        embedded = [embedded_file_data]
        if recurse:
            embedded.extend(self._unwrap_attachments(embedded, recurse=True))

        return embedded

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
            return '', None

        attachment_binary_data = attachment_node.find('./{*}EmbeddedDocumentBinaryObject')
        if attachment_binary_data is not None \
                and attachment_binary_data.attrib.get('mimeCode') in ('application/xml', 'text/xml'):
            with suppress(etree.XMLSyntaxError, binascii.Error):
                content_1 = b64decode(attachment_binary_data.text)
                return content_1, etree.fromstring(content_1)

        external_reference = attachment_node.find('./{*}ExternalReference')
        if external_reference is not None:
            description = external_reference.findtext('./{*}Description')
            mime_code = external_reference.findtext('./{*}MimeCode')

            if description and mime_code in ('application/xml', 'text/xml'):
                content_2 = description.encode('utf-8')
                with suppress(etree.XMLSyntaxError):
                    return content_2, etree.fromstring(content_2)

        # If neither EmbeddedDocumentBinaryObject nor ExternalReference/Description can be decoded as an XML,
        # fall back on the contents of EmbeddedDocumentBinaryObject.
        return content_1, None

    def _get_edi_decoder(self, file_data, new=False):
        def _get_child_models(model):
            child_models = {model}
            for child in self.env.registry[model]._inherit_children:
                child_models.update(_get_child_models(child))
            return child_models

        importable_models = [
            *_get_child_models('account.edi.xml.ubl_20'),
            *_get_child_models('account.edi.xml.cii'),
        ]

        if file_data['import_file_type'] in importable_models:
            return {
                'priority': 20,
                'decoder': self.env[file_data['import_file_type']]._import_invoice_ubl_cii,
            }
        return super()._get_edi_decoder(file_data, new)

    def _need_ubl_cii_xml(self, ubl_cii_format):
        self.ensure_one()
        return not self.ubl_cii_xml_id \
            and self.is_sale_document() \
            and ubl_cii_format in self.env['res.partner']._get_ubl_cii_formats()

    @api.model
    def _get_line_vals_list(self, lines_vals):
        """ Get invoice line values list.

        :param list[tuple] lines_vals: List of values ``[(name, qty, price, tax), ...]``.
        :returns: List of invoice line values.
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
