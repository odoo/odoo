# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class L10nItDdt(models.Model):
    _name = 'l10n.it.ddt'

    invoice_id = fields.One2many('account.invoice', 'ddt_id', string='Invoice Reference',
                                 ondelete='cascade')

    name = fields.Char(string="Numero DDT", size=20, help="Transport document number", required=True)
    transport_document_date = fields.Date(string="Data DDT", help="Transport document date", required=True)
