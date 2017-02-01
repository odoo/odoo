# -*- coding: utf-8 -*-

from openerp import models, fields, api

class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'
    x_cod_proveedor = fields.Many2one('tipo.identificacion', 'Código de Identificación Proveedor', required=False)
    x_cod_cliente = fields.Many2one('tipo.identificacion', 'Código de Identificación Cliente', required=False)
    x_identificacion = fields.Char('Número de Identificacion')
    x_parte_relacionada = fields.Boolean('¿Parte Relacionada?', default=False)
    x_contribuyente_esp = fields.Char('Contribuyente Especial')
    x_obligado_cont = fields.Boolean('¿Obligado a llevar Contabilidad?', default=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: