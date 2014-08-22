# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2014 OpenERP SA (<https://www.odoo.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import api, fields, models
from openerp.exceptions import Warning
from openerp.tools.translate import _
from pyPdf import PdfFileReader
import StringIO


class CustomerWizard(models.TransientModel):
    _name = 'print_docsaway.customer_wizard'
    _rec_name = 'remaining'

    @api.model
    def _default_currency(self):
        return self.env['print.docsaway']._get_currency()


    @api.model
    def _default_ink(self):
        return self.env['print.docsaway']._get_ink()


    @api.model
    def _default_free_count(self):
        return self.env['print.docsaway']._get_free_count()


    price = fields.Float('Cost to Deliver', compute='_compute_price', digits=(16,2))
    balance = fields.Float('Current DocsAway Balance', compute='_compute_price', digits=(16,2))
    remaining = fields.Float('Remaining DocsAway Balance', compute='_compute_price', digits=(16,2))
    ink = fields.Selection([('BW', 'Black & White'),('CL', 'Colour')], 'Ink', required=True, default=_default_ink)
    require_attention = fields.Boolean("Invalid Address", compute='_compute_require_attention')
    currency_id = fields.Many2one('res.currency', string='Currency',
        required=True, readonly=True, default=_default_currency, track_visibility='always')
    free_count = fields.Integer("Remaining Free Letters", default=_default_free_count)
    count_valid_mails = fields.Integer("Valid Mails", compute='_compute_valid_mails')
    wiz_ids = fields.One2many('print_docsaway.single_wizard', 'wizard_customer_id', string='Mails')
    attachment_ids = fields.Many2many('ir.attachment', 'message_attachment_rel',
        'message_id', 'attachment_id', 'Attachments')

    @api.multi
    def action_send_document_mails(self):
        # First check if documents are PDF and free mail, and if not overtake it
        for att in self.attachment_ids:
            if not att.name.endswith('.pdf'):
                raise Warning(
                    att.name + ': ' + _('not a PDF file.'))

        dummy1, dummy2, sass_account = self.env['print.docsaway']._get_credentials()
        if sass_account:
            company_id = self.env.user.company_id
            company_id._check_send_free_docsaway(self.count_valid_mails)

        for rec in self:
            for mail in rec.wiz_ids:
                if mail.address_valid:
                    for att in rec.attachment_ids:
                        mail.mail_id.pdf = att.datas
                        mail.mail_id._send_mail()
                mail.mail_id.unlink()
        return {'type': 'ir.actions.act_window_close'}

    @api.onchange('ink')
    def _on_change_ink(self):
        # Creating the wiz_ids now allow to show an "well formed" wizard with
        # empty list instead of a pure blank wizard
        wiz_id = self.id
        my_wiz_ids = self.env['print_docsaway.single_wizard'].search([('wizard_customer_id','=',wiz_id)])
        if len(my_wiz_ids) == 0:
            active_ids = self._context.get('active_ids', [])
            self.wiz_ids = self.env['print.docsaway']._prepare_document_deliveries(active_ids, wiz_id, ink=self.ink)
        else:
            self.wiz_ids = my_wiz_ids
            for wiz in self.wiz_ids:
                wiz.mail_id.ink = self.ink

    @api.onchange('attachment_ids')
    def _on_change_attachment_ids(self):
        # Here compute an array with the lenght
        lengths = []
        active_ids = []
        if len(self.attachment_ids) > 0:
            # Check if PDF files
            for att in self.attachment_ids:
                if not att.name.endswith('.pdf'):
                    raise Warning(
                        att.name + ': ' + _('not a PDF file.'))
                output = StringIO.StringIO(att.datas.decode('base64','strict'))
                pdf_document = PdfFileReader(output)
                length = pdf_document.getNumPages()
                lengths.append(length)
                output.close()
        for rec in self.wiz_ids:
            rec.mail_id.write({'attachment_ids': self.attachment_ids})
            active_ids.append(rec.mail_id.id)
        mail_ids = self.env['print.docsaway'].browse(active_ids)
        mail_ids._compute_multiple_price_with_attachments(mail_ids, lengths, self.balance)



    @api.one
    @api.depends('wiz_ids')
    def _compute_require_attention(self):
        for mail in self.wiz_ids:
            if mail.partner_id and not mail.mail_id._check_address_soft(mail.partner_id):
                self.require_attention = True
                return
        self.require_attention = False


    @api.one
    @api.depends('ink', 'wiz_ids.price')
    def _compute_price(self):
        if self.wiz_ids:
            self.price = sum(mail.price for mail in self.wiz_ids)
            self.balance = self.wiz_ids[-1].balance
            self.remaining = self.balance - self.price
        else:
            self.price = 0.0
            self.balance = 0.0
            self.remaining = 0.0

    @api.one
    @api.depends('wiz_ids')
    def _compute_valid_mails(self):
        valid = 0
        for mail in self.wiz_ids:
            for att in self.attachment_ids:
                if mail.address_valid:
                    valid += 1
        self.count_valid_mails = valid
