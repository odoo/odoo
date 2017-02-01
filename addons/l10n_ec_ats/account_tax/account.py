# -*- coding: utf-8 -*-

from openerp import models, fields, api

class AccountTax(models.Model):
    _name = 'account.tax'
    _inherit = 'account.tax'

    x_codigo_retencion = fields.Many2one('codigo.retencion', 'Código de Retención', required=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: