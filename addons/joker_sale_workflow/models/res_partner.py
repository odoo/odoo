# -*- coding: utf-8 -*-

from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    sale_workflow_id = fields.Many2one(
        'joker.sale.workflow',
        string='Varsayılan Satış İş Akışı',
        help='Bu müşteri için varsayılan satış iş akışı'
    )
    
    auto_invoice = fields.Boolean(
        string='Otomatik Fatura',
        default=False,
        help='Bu müşterinin siparişleri için otomatik fatura oluştur'
    )
