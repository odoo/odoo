# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import binascii
import contextlib
from itertools import chain
from xml.etree import ElementTree

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv.expression import AND
from odoo.tools import SQL


class DocumentsDocument(models.Model):
    _inherit = 'documents.document'

    # once we parsed the XML to know if a PDF is embedded inside,
    # we store that information so we don't need to parse it again
    has_embedded_pdf = fields.Boolean('Has Embedded PDF', compute='_compute_has_embedded_pdf', store=True)

    @api.depends('has_embedded_pdf')
    def _compute_thumbnail(self):
        """Compute the thumbnail and thumbnail status.

        If the XML invoices contain an embedded PDF, the thumbnail / thumbnail_status
        must have the same behavior as a standard PDF.
        """
        xml_documents = self.filtered(lambda doc: doc.has_embedded_pdf)
        xml_documents.thumbnail = False
        xml_documents.thumbnail_status = 'client_generated'
        super(DocumentsDocument, self - xml_documents)._compute_thumbnail()

    @api.depends('checksum')
    def _compute_has_embedded_pdf(self):
        for document in self:
            document.has_embedded_pdf = bool(document._extract_pdf_from_xml())

    def _extract_pdf_from_xml(self):
        """Parse the XML file and return the PDF content if one is found.

        For some invoice files (in the XML format), we can have a PDF embedded inside
        in base 64. We want to be able to preview it in documents.

        We support the UBL format
        > https://docs.peppol.eu/poacc/billing/3.0/syntax/ubl-invoice
        """
        self.ensure_one()

        if not self.mimetype or not self.raw:
            return False

        if not (self.mimetype.endswith('/xml')
                or (self.mimetype == 'text/plain' and self.name.lower().endswith('.xml'))):
            return False

        try:
            xml_file_content = self.with_context(bin_size=False).raw.decode()
        except UnicodeDecodeError:
            return False

        # quick filters, to not parse the XML most of the cases
        if "EmbeddedDocumentBinaryObject" not in xml_file_content and "Attachment" not in xml_file_content:
            return False

        try:
            tree = ElementTree.fromstring(xml_file_content)
        except ElementTree.ParseError:
            return False

        attachment_nodes = tree.iterfind('.//{*}EmbeddedDocumentBinaryObject')
        attachment_nodes = chain(attachment_nodes, tree.iterfind('.//{*}Attachment'))

        for attachment_node in attachment_nodes:
            if len(attachment_node):  # the node has children
                continue

            with contextlib.suppress(TypeError, binascii.Error):
                # check file header in case many file are embedded in the XML
                if (pdf_attachment_content := base64.b64decode(attachment_node.text + "====")).startswith(b'%PDF-'):
                    return pdf_attachment_content

        return False

    def account_create_account_move(self, move_type, journal_id=None, partner_id=None, skip_activities=False):
        if not skip_activities:
            for record in self:
                record.activity_ids.action_feedback(feedback="completed")
        if any(document.type == 'folder' for document in self):
            raise UserError(_('You can not create account move on folder.'))

        if journal_id is None:
            company_journals = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(self.env.company),
            ])
            if move_type == 'statement':
                journal_id = company_journals.filtered(lambda journal: journal.type == 'bank')[:1]
            else:
                move = self.env['account.move'].new({'move_type': move_type})
                journal_id = move.suitable_journal_ids[:1]._origin
        elif isinstance(journal_id, int):
            journal_id = self.env['account.journal'].browse(journal_id)

        move = None
        invoices = self.env['account.move']

        # 'entry' are outside of document loop because the actions
        #  returned could be differents (cfr. l10n_be_soda)
        if move_type == 'entry':
            return journal_id.create_document_from_attachment(attachment_ids=self.attachment_id.ids)

        for document in self:
            partner = partner_id or document.partner_id
            if document.res_model == 'account.move' and document.res_id:
                move = self.env['account.move'].browse(document.res_id)
            else:
                creation_context = {'default_move_type': move_type}
                if move_type in ('in_invoice', 'in_refund') and partner and 'property_purchase_currency_id' in partner:
                    supplier_currency = partner.with_company(document.company_id).property_purchase_currency_id
                    if supplier_currency:
                        creation_context['default_currency_id'] = supplier_currency.id
                move = journal_id\
                    .with_context(**creation_context)\
                    ._create_document_from_attachment(attachment_ids=document.attachment_id.id)
            if partner:
                move.partner_id = partner
            if move.statement_line_id:
                move['suspense_statement_line_id'] = move.statement_line_id.id

            invoices |= move

        # When running an action on several documents, this method is called in a
        # loop (because of the "multi" server action). When it is the case, we try
        # to redirect to a list of all created invoices instead of just the last
        # one, using the context.
        action_name_ref = {
            'in_invoice': self.env._("Vendor Bills"),
            'in_refund': self.env._("Vendor Refunds"),
            'in_receipt': self.env._("Vendor Receipts"),
            'out_invoice': self.env._("Customer Invoices"),
            'out_refund': self.env._("Customer Credit Notes"),
        }
        context = dict(self._context, default_move_type=move_type)
        documents_active_ids = context.get('documents_active_ids')
        if context.get('active_model') != 'documents.document' or not documents_active_ids:
            invoice_ids = invoices.ids
        else:
            invoice_ids = self.browse(documents_active_ids).mapped('res_id')
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'name': action_name_ref[move_type],
            'view_id': False,
            'view_mode': 'list',
            'views': [(False, "list"), (False, "form")],
            'domain': [('id', 'in', invoice_ids)],
            'context': context,
        }
        if len(invoice_ids) == 1:
            record = move or invoices[0]
            view_id = record.get_formview_id() if record else False
            action.update({
                'view_mode': 'form',
                'views': [(view_id, "form")],
                'res_id': invoice_ids[0],
                'view_id': view_id,
            })
        return action

    def account_create_account_bank_statement(self, journal_id=None):
        # It is not possible to link the doc
        # to the newly created entry as they can be more than one. But importing
        # many times the same bank statement is later checked.
        default_journal = journal_id or self.env['account.journal'].search([
            *self.env['account.journal']._check_company_domain(self.env.company),
            ('type', '=', 'bank'),
        ], limit=1)

        if not default_journal:
            error_msg = self.env['account.journal']._build_no_journal_error_msg(self.env.company.display_name, ['bank'])
            raise UserError(error_msg)

        return default_journal.create_document_from_attachment(attachment_ids=self.attachment_id.ids)

    def _get_gc_clear_bin_domain(self):
        query_folder_id = self.env['documents.account.folder.setting']._search(
            [('folder_id', '!=', False)]
        ).select('folder_id')
        return AND([
            super()._get_gc_clear_bin_domain(),
            [('id', 'not in', SQL("(%s)", query_folder_id))],
        ])
