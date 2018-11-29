# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class DocumentOrderData(models.Model):
    _name = 'document.order.data'

    invoice_id = fields.Many2one('account.invoice', string='Invoice Reference',
                                 ondelete='cascade', index=True)

    document_order_data = fields.Selection([
        ("DatiOrdineAcquisto", "Purchase order data"),
        ("DatiContratto", "Contract data"),
        ("DatiConvenzione", "Agreement data"),
        ("DatiRicezione", "Reception data"),
        ("DatiFattureCollegate", "Data of connected invoices")],
                                           string="Document order",
                                           required=True,
                                           default='DatiOrdineAcquisto')
    document_id = fields.Char(string="Document ID", help="Identify the number of the document", size=20)
    date_document_id = fields.Date(string="Generated date of document", help="To indicate the date of generation of the document")
    document_agreement_code = fields.Char("Order or agreement code", size=100)
    document_project_code_cup = fields.Char(string="Project code (CUP)",
                                            help="Indicate the code managed by the CIPE [Interdepartmental\
        committee for economic programming] which is assigned to every public\
        investment project (Project Code) and to guarantee the traceability of\
        the payment on the part of the PA.", size=15)
    document_tender_code_cig = fields.Char(string="Tender code (CIG)",
                                           help="Indicate the identification code of the tender\
                                           procedure and to guarantee the traceability of the\
                                           payment by the PA.", size=15)
