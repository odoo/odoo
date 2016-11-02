# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = ['account.invoice', 'base.edi']

    @api.multi
    def edi_generate_attachment_filename(self):
        return 'invoice_filename.xml'

    def edi_attach_business_file(self):
        self.ensure_one()
        assert self.type in ('out_invoice', 'out_refund')
        assert self.state in ('open', 'paid')
        filename = self.edi_generate_attachment_filename()
        edi_document = self.create_business_document(self.partner_id.template)
        if not edi_document:
            return None
        # template_str = self.tree_node_as_str(template_node)
        return self._create_pdf_attachment(filename, edi_document)
