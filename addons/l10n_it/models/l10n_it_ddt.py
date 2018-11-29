# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class L10nItDdt(models.Model):
    _name = 'l10n.it.ddt'

    invoice_line_id = fields.Many2many('account.invoice.line', string='Invoice Line Reference', readonly=True)
    # invoice_line_id = fields.One2many('account.invoice.line', 'ddt_line_ids', string='Product Reference', readonly=True)
    invoice_id = fields.One2many('account.invoice', 'ddt_id', string='Invoice Reference',
                                 ondelete='cascade')

    name = fields.Char(string="Numero DDT", size=20, help="Transport document number", required=True)
    transport_document_date = fields.Date(string="Data DDT", help="Transport document date", required=True)
