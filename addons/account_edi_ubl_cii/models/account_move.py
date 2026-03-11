from base64 import b64decode
from contextlib import suppress
import binascii
import re

from lxml import etree

from odoo import _, api, fields, models, Command
from odoo.tools.mimetypes import guess_mimetype
from odoo.exceptions import UserError
from odoo.tools import frozendict


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
    ubl_cii_xml_filename = fields.Char(
        string="UBL/CII Filename",
        compute='_compute_filename',
    )

    # -------------------------------------------------------------------------
    # COMPUTE
    # -------------------------------------------------------------------------

    @api.depends('ubl_cii_xml_file')
    def _compute_filename(self):
        """ Compute the filename based on the uploaded file. """
        for record in self:
            record.ubl_cii_xml_filename = record.ubl_cii_xml_id.name

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------

    def action_invoice_download_ubl(self):
        return {
            'type': 'ir.actions.act_url',
            'url': f'/account/download_invoice_documents/{",".join(map(str, self.ids))}/ubl?allow_fallback=true',
            'target': 'download',
        }

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

    def action_group_ungroup_lines_by_tax(self):
        """
        This action allows the user to reload an imported move, grouping or not lines by tax
        """
        self.ensure_one()
        self._check_move_for_group_ungroup_lines_by_tax()

        if self._has_lines_grouped():
            self._ungroup_lines()
        else:
            self._group_lines_by_tax()

    def _ungroup_lines(self):
        """
        Ungroup lines using the original file, used to import the move
        """
        self.ensure_one()
        error_message = self.env._("Cannot find the origin file, try by importing it again")
        if not self.ubl_cii_xml_id:
            raise UserError(error_message)

        files_data = self._to_files_data(self.ubl_cii_xml_id)
        files_data.extend(self._unwrap_attachments(files_data))
        file_data_group = self._group_files_data_into_groups_of_mixed_types(files_data)[0]
        self.invoice_line_ids = [Command.clear()]
        if self.with_context(ungroup_lines=True)._extend_with_attachments(file_data_group):
            self._message_log(body=self.env._("Ungrouped lines from %s", file_data_group[0]['attachment'].name))
        else:
            raise UserError(error_message)

    def _group_lines_by_tax(self):
        """
        Group lines by tax, based on the invoice lines
        """
        self.ensure_one()
        line_vals = self._get_line_vals_group_by_tax(self.partner_id)
        self.invoice_line_ids = [Command.clear()]
        self.invoice_line_ids = line_vals
        self._message_log(body=self.env._("Grouped lines by tax"))

    def _get_line_vals_group_by_tax(self, partner):
        """
        Create a collection of dicts containing the values to create invoice lines, grouped by
        tax and deferred date if present.
        :param partner: partner linked to the move
        """
        self.ensure_one()
        AccountTax = self.env['account.tax']

        base_lines, _tax_lines = self._get_rounded_base_and_tax_lines()

        def aggregate_function(target_base_line, base_line):
            target_base_line.setdefault('_aggregated_quantity', 0.0)
            target_base_line['_aggregated_quantity'] += base_line['quantity']

        def grouping_function(base_line):
            return {
                '_grouping_key': frozendict(AccountTax._prepare_base_line_grouping_key(base_line)),
            }

        base_lines = AccountTax._reduce_base_lines_with_grouping_function(
            base_lines,
            grouping_function=grouping_function,
            aggregate_function=aggregate_function,
        )

        to_create = []
        for base_line in base_lines:
            taxes = base_line['tax_ids']
            account = base_line['account_id']
            to_create.append(Command.create({
                'name': " - ".join([partner.name or self.env._("Unknown partner"), account.code, " / ".join(taxes.mapped('name')) or self.env._("Untaxed")]),
                'quantity': base_line['quantity'],
                'price_unit': base_line['price_unit'],
                **base_line['_grouping_key'],
            }))
        return to_create

    def _check_move_for_group_ungroup_lines_by_tax(self):
        """
        Perform checks to evaluate if a move is eligible to grouping/ungrouping
        """
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(self.env._("You can only (un)group lines of a draft invoice"))

    def _has_lines_grouped(self):
        """
        Check if the move has its lines grouped
        :return: True if lines look like they're grouped, False otherwise
        """
        self.ensure_one()
        partner_name = re.escape(self.partner_id.name or _("Unknown partner")) + r' - \d+ - .*'
        return any(
            re.match(partner_name, line.name)
            for line in self.line_ids.filtered(lambda line: line.name and line.display_type == 'product')
        )

    @api.model
    def _post_process_link_to_purchase_order(self, invoice):
        # Override account.move
        try:
            invoice._check_move_for_group_ungroup_lines_by_tax()
        except UserError:
            return

        if (
            self.env.context.get('ungroup_lines')
            or not invoice.partner_id
            or not invoice.ubl_cii_xml_id
        ):
            return

        # Group lines
        if invoice.journal_id.type == 'sale':
            move_types = invoice.get_sale_types(include_receipts=True)
        else:
            move_types = invoice.get_purchase_types(include_receipts=True)
        last_bill_from_vendor = self.env['account.move'].search([
            ('move_type', 'in', move_types),
            ('partner_id', '=', invoice.partner_id.id),
            ('state', '=', 'posted'),
            ('id', '!=', invoice.id),
            *self.env['account.move']._check_company_domain(invoice.company_id),
        ], order='create_date desc', limit=1)
        if last_bill_from_vendor and last_bill_from_vendor._has_lines_grouped():
            invoice._group_lines_by_tax()

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
            and (self.is_sale_document() or self._is_exportable_as_self_invoice()) \
            and ubl_cii_format in self.env['res.partner']._get_ubl_cii_formats()

    def _is_exportable_as_self_invoice(self):
        return (
            self.state == 'posted'
            and self.is_purchase_document()
            and self.journal_id.is_self_billing
            and (invoice_edi_format := self.commercial_partner_id._get_peppol_edi_format())
            and (edi_builder := self.partner_id._get_edi_builder(invoice_edi_format)) is not None
            and edi_builder._can_export_selfbilling()
        )

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
