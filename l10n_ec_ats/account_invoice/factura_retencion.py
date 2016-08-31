# -*- coding: utf-8 -*-
from openerp import models, fields, api

class account_invoice(models.Model):
    _inherit = 'account.invoice'
# Campos Tributarios Factura Electrónica
#    x_tipo_emision = fields.Char('TIpo de Emisión')
    x_tipo_sustento = fields.Many2one('tipo.sustento', 'Código de Sustento')
    x_tipo_comprobante = fields.Many2one('tipo.comprobante', 'Tipo de Comprobante', required=False)
    x_fac_clave_acceso = fields.Char('Clave de Acceso Fac.', required=False)
    x_fac_codigo_documento = fields.Char('Código de Documento - Fact. Elec', required=False)
    x_fac_establecimiento = fields.Char('Establecimiento Fac.', required=False)
    x_fac_punto_emision = fields.Char('Punto de Emision Fac.', required=False)
    x_fac_secuencial = fields.Char('Secuencial Fac.', required=False)
    x_fac_autorizacion = fields.Char('Autorización Fac.', required=False)
# Campos Tributarios Retención Electrónica
#    x_fac_ambiente = fields.Char('Ambiente')
#    x_tipo_emision = fields.Char('TIpo de Emisión')
    x_ret_clave_acceso = fields.Char('Clave de Acceso Ret.', required=False)
    x_ret_codigo_documento = fields.Char('Código de Documento - Ret. Elec', required=False)
    x_ret_fecha_emision = fields.Date('Fecha Retención', required=False)
    x_ret_establecimiento = fields.Char('Establecimiento Ret.', required=False)
    x_ret_punto_emision = fields.Char('Punto de Emisión Ret.', required=False)
    x_ret_secuencial = fields.Char('Secuencial Ret.', required=False)
    x_ret_autorizacion = fields.Char('Autorización Ret.', required=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: