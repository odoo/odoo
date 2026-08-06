# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import cleanup_xml_node


class CoretaxDocument(models.Model):
    _name = "l10n_id_efaktur_coretax.document"
    _description = "Coretax Document"
    _inherit = ["mail.thread.main.attachment", "mail.activity.mixin"]

    name = fields.Char(compute="_compute_name", store=True)
    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)
    active = fields.Boolean(string="Active", default=True)
    document_type = fields.Selection(
        selection=[
            ('efaktur', "E-Faktur"),
        ],
        string="Document Type",
        required=True,
        default='efaktur',
        readonly=True,
    )
    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        string="Attachments",
        copy=False,
        readonly=True,
    )

    # Source records
    invoice_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="l10n_id_coretax_document",
        domain="[('move_type', 'in', ['out_invoice', 'out_refund']), ('company_id', '=', company_id), ('l10n_id_coretax_document', '=', False), ('state', '=', 'posted')]",
    )

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('document_type', 'invoice_ids')
    def _compute_name(self):
        for doc in self:
            source_records = doc._get_source_records()
            sorted_records = source_records.sorted('name') if source_records else doc.browse()
            name_parts = []
            if sorted_records:
                name_parts.append(sorted_records[0].name)
                if len(sorted_records) > 1:
                    name_parts.append(sorted_records[-1].name)
            doc.name = "%s - %s (%s)" % (
                fields.Date.context_today(doc).strftime("%Y%m%d"),
                doc._get_document_type_label(),
                "....".join(name_parts),
            )

    # ----------------
    # Generic methods
    # ----------------

    def _get_document_type_label(self):
        self.ensure_one()
        return dict(self._fields['document_type']._description_selection(self.env))[self.document_type]

    def _get_source_records(self):
        """ The records this document is filed for, whichever model they belong to. """
        self.ensure_one()
        return {
            'efaktur': self.invoice_ids,
        }.get(self.document_type)

    def _get_xml_files(self):
        """ Build the XML files for this document.

        :return: a list of {'name': the file name, without extension, 'xml': the file content as bytes}
        """
        self.ensure_one()
        if not self._get_source_records():
            raise UserError(_("No records found to generate %s.", self._get_document_type_label()))
        return {
            'efaktur': self._get_xml_files_efaktur,
        }.get(self.document_type)()

    def _generate_xml(self, regenerate=False):
        """ Generate the XML files and save them as attachments on this record. """
        self.ensure_one()

        xml_files = self._get_xml_files()

        self.attachment_ids.unlink()
        attachments = self.env['ir.attachment'].create([{
            'name': f'{xml_file["name"]}.xml',
            'type': 'binary',
            'raw': xml_file['xml'],
            'mimetype': 'application/xml',
            'res_model': self._name,
            'res_id': self.id,
        } for xml_file in xml_files])
        self.attachment_ids = [fields.Command.set(attachments.ids)]

        self.message_post(
            body=(
                _("The %s report has been re-generated", self._get_document_type_label())
                if regenerate else
                _("The %s report has been generated", self._get_document_type_label())
            ),
            attachments=[(attachment.name, attachment.raw) for attachment in attachments],
        )

    def action_download(self):
        """ Download the document files, generating them first if needed. """
        for document in self.filtered(lambda doc: doc._get_source_records()):
            if not document.attachment_ids:
                document._generate_xml()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/l10n_id_efaktur_coretax/download_attachments/{",".join(map(str, self.attachment_ids.ids))}',
        }

    def action_regenerate(self):
        self._generate_xml(regenerate=True)

    # --------
    # E-Faktur
    # --------

    def _get_xml_files_efaktur(self):
        # Validate invoices before generating E-Faktur.
        no_transaction_code_entries = self.invoice_ids.filtered(lambda invoice: not invoice.l10n_id_kode_transaksi)
        non_invoice_entries = self.invoice_ids.filtered(lambda invoice: invoice.move_type != 'out_invoice')

        if no_transaction_code_entries:
            raise UserError(_("Some documents don't have a transaction code: %s", ", ".join(no_transaction_code_entries.mapped('name'))))
        if non_invoice_entries:
            raise UserError(_("Some documents are not Customer Invoices: %s", ", ".join(non_invoice_entries.mapped('name'))))

        return [{
            'name': 'efaktur_%s' % fields.Datetime.to_string(fields.Datetime.now()).replace(" ", "_"),
            'xml': self._generate_efaktur_invoice(),
        }]

    def _generate_efaktur_invoice(self):
        """ Generate the E-Faktur XML for customer invoices. """
        xml_content = self.env['ir.qweb']._render(
            'l10n_id_efaktur_coretax.efaktur_coretax_template',
            {'data': self.invoice_ids.prepare_efaktur_vals(), 'TIN': self.company_id.vat},
        )
        return etree.tostring(
            cleanup_xml_node(xml_content, remove_blank_text=False, remove_blank_nodes=False),
            xml_declaration=True,
            encoding='UTF-8',
        )
