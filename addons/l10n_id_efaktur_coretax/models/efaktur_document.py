# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import  _, api, fields, models
from odoo.exceptions import UserError
from lxml import etree
from odoo.tools import cleanup_xml_node


class EfakturDocument(models.Model):
    _name = "l10n_id_efaktur_coretax.document"
    _description = "E-Faktur Document"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(compute="_compute_name", store=True)
    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)
    active = fields.Boolean(
        string="Active",
        default=True,
    )
    invoice_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="l10n_id_coretax_document",
        domain="[('move_type', 'in', ['out_invoice', 'out_refund']), ('company_id', '=', company_id), ('l10n_id_coretax_document', '=', False), ('state', '=', 'posted')]",
    )
    attachment_id = fields.Many2one(comodel_name="ir.attachment", readonly=True)

    @api.depends('invoice_ids')
    def _compute_name(self):
        for doc in self:
            sorted_invoices = doc.invoice_ids.sorted('name')
            name = []
            if sorted_invoices:
                name.append(sorted_invoices[0].name)
                if len(sorted_invoices) > 1:
                    name.append(sorted_invoices[-1].name)
            doc.name = "%s - Efaktur (%s)" % (fields.Date.context_today(doc).strftime("%Y%m%d"), "....".join(name))

    def action_download(self):
        """ Download E-Faktur of related attachment """
        for document in self.filtered(lambda doc: doc.invoice_ids):
            if not document.attachment_id:
                document._generate_xml()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/l10n_id_efaktur_coretax/download_attachments/{",".join(map(str, self.attachment_id.ids))}',
        }

    def _generate_xml(self, regenerate=False):
        """ Generate the XML file as content and save it as attachment in this record"""
        self.ensure_one()

        # invalid journal entries to generate efaktur
        no_trx_code_entries = self.invoice_ids.filtered(lambda x: not x.l10n_id_kode_transaksi)
        non_invoice_entries = self.invoice_ids.filtered(lambda x: x.move_type != 'out_invoice')

        if no_trx_code_entries:
            raise UserError(_("Some documents don't have a transaction code: %s", ", ".join(no_trx_code_entries.mapped('name'))))
        if non_invoice_entries:
            raise UserError(_("Some documents are not Customer Invoices: %s", ", ".join(non_invoice_entries.mapped('name'))))
        raw_data = self._generate_efaktur_invoice()

        if not self.attachment_id:
            attachment = self.env['ir.attachment'].create({
                'raw': raw_data,
                'name': 'efaktur_%s.xml' % (fields.Datetime.to_string(fields.Datetime.now()).replace(" ", "_")),
                'type': 'binary',
                'res_model': 'l10n_id_efaktur_coretax.document',
                'res_id': self.id,
            })
            self.attachment_id = attachment.id
        else:
            attachment = self.attachment_id
            self.attachment_id.write({
                'raw': raw_data,
                'name': 'efaktur_%s.xml' % (fields.Datetime.to_string(fields.Datetime.now()).replace(" ", "_")),
            })

        if not regenerate:
            message = _("The e-Faktur report has been generated")
        else:
            message = _("The e-Faktur report has been re-generated")

        self.message_post(
            body=message,
            attachments=[(attachment.name, attachment.raw)]
        )

    def _generate_efaktur_invoice(self):
        """ Generate E-Faktur for customer invoice. Prepare data, load XML template and """
        invoice_data = self.invoice_ids.prepare_efaktur_vals()
        xml_content = self.env['ir.qweb']._render('l10n_id_efaktur_coretax.efaktur_coretax_template', {'data': invoice_data, 'TIN': self.company_id.vat})
        return etree.tostring(cleanup_xml_node(xml_content, remove_blank_text=False, remove_blank_nodes=False), xml_declaration=True, encoding='UTF-8')

    def action_regenerate(self):
        self._generate_xml(regenerate=True)
