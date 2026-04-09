# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from lxml import etree
from odoo.tools import cleanup_xml_node


class EBupotDocument(models.Model):
    _name = "l10n_id_efaktur_coretax.ebupot.document"
    _description = "E-Bupot Document"
    _inherit = ["mail.thread.main.attachment", "mail.activity.mixin"]

    name = fields.Char(compute="_compute_name", store=True)
    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)
    active = fields.Boolean(
        string="Active",
        default=True,
    )
    payment_ids = fields.One2many(
        comodel_name="account.payment",
        inverse_name="l10n_id_ebupot_document_xml",
        domain="[('company_id', '=', company_id), ('l10n_id_ebupot_document_xml', '=', False)]",
    )
    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        string="Attachments",
        readonly=True
    )

    @api.depends('payment_ids')
    def _compute_name(self):
        for doc in self:
            sorted_payments = doc.payment_ids.sorted('name')
            name = []
            if sorted_payments:
                name.append(sorted_payments[0].name)
                if len(sorted_payments) > 1:
                    name.append(sorted_payments[-1].name)
            doc.name = "%s - E-Bupot (%s)" % (fields.Date.context_today(doc).strftime("%Y%m%d"), "....".join(name))

    def action_download(self):
        """ Download E-Bupot of related attachment """
        for document in self.filtered(lambda doc: doc.payment_ids):
            if not document.attachment_ids:
                document._generate_xml()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/l10n_id_efaktur_coretax/ebupot/download_attachments/{",".join(map(str, self.attachment_ids.ids))}',
        }

    def _generate_xml(self, regenerate=False):
        """ Generate the XML file as content and save it as attachment in this record"""
        self.ensure_one()

        if not self.payment_ids:
            raise UserError(_("No payments found to generate E-Bupot."))

        xml_list = self._generate_ebupot_invoice()
        attachments = []
        for item in xml_list:
            filename = f'{item["tax"]}.xml'
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'raw': item['xml'],
                'mimetype': 'application/xml',
                'res_model': self._name,
                'res_id': self.id,
            })
            attachments.append(attachment.id)
        self.attachment_ids = [(6, 0, attachments)]
        message = (
            _("The E-Bupot report has been generated")
            if not regenerate else
            _("The E-Bupot report has been re-generated")
        )
        self.message_post(
            body=message,
            attachment_ids=attachments
        )

    def _generate_ebupot_invoice(self):
        """ Generate E-Bupot XML """

        all_vals = self.payment_ids.prepare_ebupot_vals()
        xml_content = self.env['ir.qweb']._render('l10n_id_efaktur_coretax.ebupot_template', {'data': all_vals, 'TIN': self.company_id.vat})
        xml_bytes = etree.tostring(cleanup_xml_node(xml_content, remove_blank_text=False, remove_blank_nodes=False), xml_declaration=True, encoding='UTF-8')
        return [{
            'tax': f'ebupot_{fields.Date.context_today(self).strftime("%Y%m%d")}',
            'xml': xml_bytes,
        }]

    def action_regenerate(self):
        self._generate_xml(regenerate=True)
