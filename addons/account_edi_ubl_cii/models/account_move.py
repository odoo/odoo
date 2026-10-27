# -*- coding: utf-8 -*-
import logging
import re

from collections import defaultdict

from odoo import _, api, fields, models, Command
from odoo.exceptions import UserError

from .account_edi_xml_preview import preview_token, xml_tree_to_html
from .account_edi_xml_reader import read_invoice

_logger = logging.getLogger(__name__)


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
        error_message = _("Cannot find the origin file, try by importing it again")
        if not self.ubl_cii_xml_id:
            raise UserError(error_message)

        file_data = self.ubl_cii_xml_id._unwrap_edi_attachments()[0]
        decoder = self._get_edi_decoder(file_data)
        if decoder is None:
            raise UserError(_("Cannot decode origin file, try by importing it again"))

        self.invoice_line_ids = [Command.clear()]
        if decoder(self, file_data):
            self._message_log(body=_("Ungrouped lines from %s", file_data['attachment'].name))
        else:
            raise UserError(error_message)

    def _group_lines_by_tax(self):
        """
        Group lines by tax, based on the invoice lines
        """
        self.ensure_one()
        if not self.is_invoice(include_receipts=True):
            raise UserError(_("You can only group lines of an invoice"))

        tax_lines = self.line_ids.filtered('tax_line_id')
        tax_amounts = defaultdict(lambda: {
            'tax_amount_currency': 0.0,
            'tax_amount': 0.0,
        })
        for tax_line in tax_lines:
            tax_amounts[tax_line.tax_key]['tax_amount_currency'] += tax_line.amount_currency
            tax_amounts[tax_line.tax_key]['tax_amount'] += tax_line.balance

        currency = self.currency_id
        old_tax_amount = currency.round(sum(tax_line.amount_currency for tax_line in self.line_ids.filtered('tax_line_id')))

        line_vals = self._get_line_vals_group_by_tax(self.partner_id, fields.Date.to_string(self.date))
        self.invoice_line_ids = [Command.clear()]
        self.invoice_line_ids = line_vals

        self._message_log(body=_("Grouped lines by tax"))

        # Correct Tax Amount if a difference of 0.01 or less is detected
        new_tax_amount = currency.round(sum(tax_line.amount_currency for tax_line in self.line_ids.filtered('tax_line_id')))
        difference = currency.round(new_tax_amount - old_tax_amount)
        if currency.is_zero(difference) or currency.compare_amounts(difference, 0.01) > 0:
            return

        line_commands = []
        for tax_line in self.line_ids.filtered('tax_line_id'):
            tax_key = tax_line.tax_key
            if tax_key not in tax_amounts:
                continue

            expected_amounts = tax_amounts[tax_key]
            line_commands.append(Command.update(tax_line.id, {
                'amount_currency': expected_amounts['tax_amount_currency'],
                'balance': expected_amounts['tax_amount'],
            }))

        if line_commands:
            self.line_ids = line_commands

    def _get_line_vals_group_by_tax(self, partner, date):
        """
        Create a collection of dicts containing the values to create invoice lines, grouped by
        tax and deferred date if present.
        :param partner: partner linked to the move
        :param date: date of the move (string format)
        """
        self.ensure_one()
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
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("You can only (un)group lines of a draft invoice"))
        # TO REMOVE IN 18.0+ as purchase_edi_ubl_bis module is created
        if 'purchase_order_id' in self.env['account.move.line']._fields:  # purchase field
            if any(line.purchase_order_id for line in self.line_ids):
                raise UserError(_("You can only (un)group lines of an invoice not linked to a purchase order"))

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
            not invoice.partner_id
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

    @api.model
    def _get_ubl_cii_builder_from_xml_tree(self, tree):
        customization_id = tree.find('{*}CustomizationID')
        if tree.tag == '{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}CrossIndustryInvoice':
            return self.env['account.edi.xml.cii']
        ubl_version = tree.find('{*}UBLVersionID')
        if customization_id is not None:
            if 'xrechnung' in customization_id.text:
                return self.env['account.edi.xml.ubl_de']
            if customization_id.text == 'urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0':
                return self.env['account.edi.xml.ubl_nl']
            if customization_id.text == 'urn:cen.eu:en16931:2017#conformant#urn:fdc:peppol.eu:2017:poacc:billing:international:aunz:3.0':
                return self.env['account.edi.xml.ubl_a_nz']
            if customization_id.text == 'urn:cen.eu:en16931:2017#conformant#urn:fdc:peppol.eu:2017:poacc:billing:international:sg:3.0':
                return self.env['account.edi.xml.ubl_sg']
            if customization_id.text == 'urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0':
                return self.env['account.edi.xml.ubl_bis3']
        if ubl_version is not None:
            if ubl_version.text == '2.0':
                return self.env['account.edi.xml.ubl_20']
            if ubl_version.text in ('2.1', '2.2', '2.3'):
                return self.env['account.edi.xml.ubl_21']
        if customization_id is not None:
            if 'urn:cen.eu:en16931:2017' in customization_id.text:
                return self.env['account.edi.xml.ubl_bis3']

    def _get_edi_decoder(self, file_data, new=False):
        # EXTENDS 'account'
        if file_data['type'] == 'xml':
            ubl_cii_xml_builder = self._get_ubl_cii_builder_from_xml_tree(file_data['xml_tree'])
            if ubl_cii_xml_builder is not None:
                return ubl_cii_xml_builder._import_invoice_ubl_cii

        return super()._get_edi_decoder(file_data, new=new)

    def _need_ubl_cii_xml(self):
        self.ensure_one()
        return not self.ubl_cii_xml_id \
            and (self.is_sale_document() or self._is_exportable_as_self_invoice()) \
            and bool(self.partner_id.commercial_partner_id.ubl_cii_format)

    def _extend_with_attachments(self, attachments, new=False):
        # EXTENDS 'account': preview the received XML, and when a vendor bill
        # arrives without a supplier PDF, store a readable rendering as the main attachment.
        result = super()._extend_with_attachments(attachments, new=new)
        if not self.env.context.get('skip_invoice_xml_preview'):
            self._post_invoice_xml_previews(attachments, result)
        for move in self._moves_from_attachment_import(result):
            if move.is_purchase_document() and not move._incoming_supplier_pdf(attachments):
                move._attach_readable_pdf(attachments)
        return result

    def _moves_from_attachment_import(self, result):
        moves = self.env['account.move']
        if isinstance(result, dict):
            for imported in result.values():
                moves |= imported
        return moves or self.exists()

    def _incoming_supplier_pdf(self, attachments):
        """True when the upload itself contains a supplier PDF (Factur-X or a sibling PDF)."""
        self.ensure_one()
        for attachment in attachments:
            name = attachment.name or ''
            if name.endswith('_readable.pdf'):
                continue
            if 'pdf' in (attachment.mimetype or '') or name.lower().endswith('.pdf'):
                return True
        return self._has_supplier_pdf()

    def _get_xml_invoice_data(self, attachments=None):
        """Content of the first decodable electronic invoice, or ``False``."""
        self.ensure_one()
        if attachments is None:
            context_ids = self.env.context.get('invoice_xml_attachment_ids')
            if context_ids:
                attachments = self.env['ir.attachment'].browse(context_ids)
            else:
                self.invalidate_recordset(['ubl_cii_xml_id'])
                attachments = self.attachment_ids
                if self.ubl_cii_xml_id:
                    attachments |= self.ubl_cii_xml_id
        for file_data in attachments._unwrap_edi_attachments():
            try:
                data = read_invoice(file_data.get('xml_tree'))
                if data:
                    return data
            finally:
                on_close = file_data.get('on_close')
                if on_close:
                    on_close()
        return False

    def _readable_pdf_name(self, invoice_data):
        self.ensure_one()
        number = invoice_data.get('number') or self.ref or self.name or 'Invoice'
        safe = number.replace('/', '_').replace(' ', '_')
        return '%s_readable.pdf' % safe

    def _has_supplier_pdf(self):
        """A PDF that is not the readable rendering generated from the XML."""
        self.ensure_one()
        main = self.message_main_attachment_id
        if not main:
            return False
        is_pdf = 'pdf' in (main.mimetype or '') or (main.name or '').lower().endswith('.pdf')
        if not is_pdf:
            return False
        name = main.name or ''
        return not name.endswith('_readable.pdf') and 'Generated by Odoo' not in name

    def _generate_readable_pdf_from_import(self, file_data):
        """Called from ``account.edi.common._generate_pdf_attachment`` during import."""
        self.ensure_one()
        if not self.is_purchase_document():
            return self.env['ir.attachment']
        if file_data.get('originator_pdf'):
            return self.env['ir.attachment']
        if self._has_supplier_pdf():
            return self.message_main_attachment_id
        self.invalidate_recordset(['ubl_cii_xml_id'])
        return self._attach_readable_pdf()

    def _attach_readable_pdf(self, attachments=None, force=False):
        """Render the XML as a PDF and set it as the main attachment.

        A supplier PDF already present is left in place unless ``force`` is set
        by the manual button. The legal customer PDF field is not written.
        """
        self.ensure_one()
        main_name = self.message_main_attachment_id.name or ''
        if not force and main_name.endswith('_readable.pdf'):
            return self.message_main_attachment_id
        if attachments:
            pending = attachments.filtered(lambda att: not att.res_id)
            if pending:
                pending.write({'res_model': 'account.move', 'res_id': self.id})
        invoice_data = self._get_xml_invoice_data(attachments)
        if not invoice_data:
            return self.env['ir.attachment']
        if not force and self._has_supplier_pdf():
            return self.message_main_attachment_id
        try:
            render_context = {'force_report_rendering': True}
            if attachments is not None:
                render_context['invoice_xml_attachment_ids'] = attachments.ids
            pdf_content, extension = self.env['ir.actions.report'].with_context(
                **render_context,
            )._render_qweb_pdf(
                'account_edi_ubl_cii.action_report_invoice_xml_readable', res_ids=self.ids,
            )
        except Exception:
            if force:
                raise
            _logger.exception("Could not render the readable PDF for %s", self.display_name)
            return self.env['ir.attachment']
        if extension != 'pdf' or not pdf_content:
            return self.env['ir.attachment']
        filename = self._readable_pdf_name(invoice_data)
        previous = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', self.id),
            ('name', '=', filename),
        ])
        if previous:
            previous.unlink()
        attachment = self.env['ir.attachment'].with_context(
            no_new_invoice=True,
            skip_invoice_xml_preview=True,
        ).create({
            'name': filename,
            'res_model': 'account.move',
            'res_id': self.id,
            'raw': pdf_content,
            'type': 'binary',
            'mimetype': 'application/pdf',
        })
        self.with_context(tracking_disable=True).message_main_attachment_id = attachment
        return attachment

    def action_preview_invoice_xml(self):
        """Post an internal note with the received XML, once per file."""
        for move in self:
            move.invalidate_recordset(['ubl_cii_xml_id'])
            attachments = move.attachment_ids
            if move.ubl_cii_xml_id:
                attachments |= move.ubl_cii_xml_id
            if attachments:
                move._post_invoice_xml_previews(attachments, {attachment: move for attachment in attachments})
        return True

    def action_generate_readable_pdf(self):
        """Force a readable PDF from the XML and set it as the main attachment."""
        self.ensure_one()
        if not self._get_xml_invoice_data():
            raise UserError(_("No electronic invoice (UBL, CII or Factur-X) is attached to this document."))
        self._attach_readable_pdf(force=True)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }

    def _post_invoice_xml_previews(self, attachments, result):
        mapping = {}
        if isinstance(result, dict):
            for attachment, moves in result.items():
                if attachment:
                    mapping[attachment.id] = moves
        fallback = self._moves_from_attachment_import(result)
        to_scan = attachments.exists() if attachments else self.env['ir.attachment']
        if mapping:
            to_scan |= self.env['ir.attachment'].browse(list(mapping))
        for attachment in to_scan:
            moves = mapping.get(attachment.id) or fallback
            if not moves:
                continue
            for file_data in attachment._unwrap_edi_attachments():
                try:
                    if file_data.get('xml_tree') is None:
                        continue
                    for move in moves:
                        move._post_invoice_xml_preview_note(file_data)
                finally:
                    on_close = file_data.get('on_close')
                    if on_close:
                        on_close()

    def _post_invoice_xml_preview_note(self, file_data):
        self.ensure_one()
        tree = file_data.get('xml_tree')
        if tree is None:
            return
        attachment = file_data.get('attachment') or file_data.get('originator_pdf')
        filename = file_data.get('filename') or (attachment.name if attachment else '')
        token = preview_token(attachment.id if attachment else 0, filename)
        if self._invoice_xml_preview_note_exists(token):
            return
        body = xml_tree_to_html(tree, filename=filename, token=token)
        if not body:
            return
        self.with_context(no_new_invoice=True, skip_invoice_xml_preview=True).message_post(
            body=body,
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

    def _invoice_xml_preview_note_exists(self, token):
        self.ensure_one()
        needle = 'account-xml-preview:%s' % token
        messages = self.env['mail.message'].search([
            ('model', '=', self._name),
            ('res_id', '=', self.id),
            ('body', 'ilike', 'account-xml-preview:'),
        ], limit=50)
        return any(needle in (message.body or '') for message in messages)
