# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.tools.misc import format_date, file_open
from odoo.modules.module import get_resource_path

import base64
import io
from PyPDF2 import PdfFileReader, PdfFileWriter
from reportlab.pdfgen import canvas
from datetime import timedelta


class AccountTourUploadBill(models.TransientModel):
    _name = 'account.tour.upload.bill'
    _description = 'Account tour upload bill'
    _inherits = {'mail.compose.message': 'composer_id'}

    composer_id = fields.Many2one('mail.compose.message', string='Composer', required=True, ondelete='cascade')

    selection = fields.Selection(
        selection=lambda self: self._selection_values(),
        default="sample"
    )

    sample_bill_preview = fields.Binary(
        readonly=True,
        compute='_compute_sample_bill_image'
    )

    def _selection_values(self):
        values = [
            ('sample', _('Try a sample vendor bill')),
            ('upload', _('Upload your own bill')),
        ]
        journal_alias = self.env['account.journal'] \
            .search([('type', '=', 'purchase'), ('company_id', '=', self.env.company.id)], limit=1)
        if journal_alias.alias_domain:
            values += [('email', _('Or send a bill to %s@%s', journal_alias.alias_name, journal_alias.alias_domain))]
        else:
            values += [('noemail', _('Or send a bill by email'))]

        return values

    def _compute_sample_bill_image(self):
        """ Retrieve sample bill with facturx to speed up onboarding """
        def addAddress(can, x, y, partner):
            can.setFillColorRGB(1, 1, 1)
            can.rect(x, y, width*0.3, height*0.1, fill=1, stroke=0)
            can.setFillColorRGB(0.4, 0.4, 0.4)
            for i, line in enumerate(partner.split('\n')):
                if i == 0:
                    can.setFont("Helvetica-Bold", height/80)
                if i == 1:
                    can.setFont("Helvetica", height/80)
                can.drawString(x + width*0.01, y + height*0.09 - i*height/70, line)

        def addDate(can, x, y, date):
            can.setFillColorRGB(1, 1, 1)
            can.rect(x, y, width*0.1, height*0.0166, fill=1, stroke=0)
            can.setFont("Helvetica", height/80)
            can.setFillColorRGB(0.52, 0.52, 0.52)
            can.drawString(x + width/500, y + height/250, date)

        try:
            file = file_open('account_edi_facturx/data/files/Invoice.pdf', 'rb')
            pdf_reader = PdfFileReader(file)
            pdf_writer = PdfFileWriter()
            page = pdf_reader.getPage(0)
            canvas_stream = io.BytesIO()
            can = canvas.Canvas(canvas_stream)
            width = float(abs(page.mediaBox.getWidth()))
            height = float(abs(page.mediaBox.getHeight()))
            # Vendor address
            addAddress(can, width*0.15, height*0.88, (
                "Odoo\n"
                "Chaussée de Namur, 40\n"
                "1367 Grand-Rosière\n"
                "Belgium"
            ))
            # Client address
            addAddress(can, width*0.58, height*0.765, (
                "{name}\n"
                "{street}\n"
                "{street2}\n"
                "{zip} {city}\n"
                "{country}\n"
                "{vat}"
            ).format(
                name=self.env.company.name or "",
                street=self.env.company.street or "",
                street2=self.env.company.street2 or "",
                zip=self.env.company.zip or "",
                city=self.env.company.city or "",
                country=self.env.company.country_id.name or "",
                vat=self.env.company.vat or "",
            ))
            # Invoice Date
            addDate(can, width*0.05, height*0.675, format_date(self.env, fields.Date.today()))
            # Due Date
            addDate(can, width*0.182, height*0.675, format_date(self.env, fields.Date.today() + timedelta(days=7)))
            can.save()
            overlay = PdfFileReader(canvas_stream, overwriteWarnings=False).getPage(0)

            for i in range(pdf_reader.getNumPages()):
                page = pdf_reader.getPage(i)
                page.mergePage(overlay)
                pdf_writer.addPage(page)

            original_stream = io.BytesIO()
            pdf_writer.write(original_stream)
            self.sample_bill_preview = base64.b64encode(original_stream.getvalue())
            file.close()
        except (IOError, OSError):
            self.sample_bill_preview = False
        return

    def _action_list_view_bill(self, bill_ids=[]):
        return {
            'name': _('Generated Documents'),
            'domain': [('id', 'in', bill_ids)],
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'views': [[False, "tree"], [False, "form"]],
            'type': 'ir.actions.act_window',
            'context': self._context
        }

    def apply(self):
        purchase_journal = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
        if self.selection == 'upload':
            return purchase_journal.with_context(default_journal_id=purchase_journal.id, default_move_type='in_invoice').create_invoice_from_attachment(attachment_ids=self.attachment_ids.ids)
        elif self.selection == 'sample':
            attachment = self.env['ir.attachment'].create({
                'type': 'binary',
                'name': 'INV/2020/0011.pdf',
                'res_model': 'mail.compose.message',
                'datas': self.sample_bill_preview,
            })
            bill = purchase_journal.with_context(default_journal_id=purchase_journal.id, default_move_type='in_invoice')._create_invoice_from_single_attachment(attachment)
            if self.selection == 'sample':
                bill.write({
                    'partner_id': self.env.ref('base.main_partner').id,
                    'ref': 'INV/2020/0011'
                })
            return self._action_list_view_bill(bill.ids)
        else:
            email_alias = '%s@%s' % (purchase_journal.alias_name, purchase_journal.alias_domain)
            new_wizard = self.env['account.tour.upload.bill.email.confirm'].create({'email_alias': email_alias})
            view_id = self.env.ref('account.account_tour_upload_bill_email_confirm').id

            return {
                'type': 'ir.actions.act_window',
                'name': _('Confirm'),
                'view_mode': 'form',
                'res_model': 'account.tour.upload.bill.email.confirm',
                'target': 'new',
                'res_id': new_wizard.id,
                'views': [[view_id, 'form']],
            }


class AccountTourUploadBillEmailConfirm(models.TransientModel):
    _name = 'account.tour.upload.bill.email.confirm'
    _description = 'Account tour upload bill email confirm'

    email_alias = fields.Char(readonly=True)

    def apply(self):
        purchase_journal = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
        bill_ids = self.env['account.move'].search([('journal_id', '=', purchase_journal.id)]).ids
        return self.env['account.tour.upload.bill']._action_list_view_bill(bill_ids)
