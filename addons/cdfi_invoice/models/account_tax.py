# -*- coding: utf-8 -*-
from odoo import fields, models, api,_

    
class AccountTax(models.Model):
    _inherit = 'account.tax'
    
    
    impuesto = fields.Selection(selection=[('002', 'IVA'),
                                           ('003', ' IEPS'),
                                           ('001', 'ISR'),
                                           ('004', 'Impuesto Local')], string='Impuesto')
    tipo_factor = fields.Selection(selection=[('Tasa', 'Tasa'),
                                           ('Cuota', 'Cuota'),
                                           ('Exento', 'Exento')], string='Tipo factor')
    impuesto_local = fields.Char('Impuesto Local')
