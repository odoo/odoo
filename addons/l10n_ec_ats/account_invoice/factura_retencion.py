# -*- coding: utf-8 -*-
from openerp import models, fields, api

class account_invoice(models.Model):
    _inherit = 'account.invoice'
# Computo del IVA para la impresion QWeb
    x_impuesto = fields.Monetary(string='Impuesto', store=True, readonly=True, compute='_compute_impuesto')
# Secuencial del documento Impreso Company
    x_company_establecimiento = fields.Char(string='Mi Establecimiento', store=True, readonly=True, compute='_compute_establecimiento',\
                                            help = "Este campo se llena automaticamente cuando valida el documento, por favor configurar el Secuencial con el formato 001-001-000000001")
    x_company_emision = fields.Char(string='Mi Punto de Emision', store=True, readonly=True, compute='_compute_emision',\
                                            help = "Este campo se llena automaticamente cuando valida el documento, por favor configurar el Secuencial con el formato 001-001-000000001")
    x_company_secuencial = fields.Char(string='Mi Secuencial', store=True, readonly=True, compute='_compute_secuencial',\
                                            help = "Este campo se llena automaticamente cuando valida el documento, por favor configurar el Secuencial con el formato 001-001-000000001")
    x_company_autorizacion = fields.Char('Mi Autorización', required=False,\
                                            help = "Seleccionar 'Open Debug Menu => Set Defaults' y establecer el número de autorizacion por defecto")
    # Secuencial del documento Impreso Partner
    x_partner_establecimiento = fields.Char('Partner Establecimiento', required=False)
    x_partner_punto_emision = fields.Char('Partner Punto de Emisión', required=False)
    x_partner_secuencial = fields.Char('Partner Secuencial', required=False)
    x_partner_autorizacion = fields.Char('Partner Autorización', required=False)
# Campos Tributarios Factura Electrónica
#    x_tipo_emision = fields.Char('TIpo de Emisión')
    x_tipo_sustento = fields.Many2one('tipo.sustento', 'Código de Sustento')
    x_tipo_comprobante = fields.Many2one('tipo.comprobante', 'Tipo de Comprobante', required=False)
    x_fac_clave_acceso = fields.Char('Clave de Acceso Fac.', required=False)
    x_fac_codigo_documento = fields.Char('Código de Documento - Fact. Elec', required=False)
# Campos Tributarios Retención Electrónica
#    x_fac_ambiente = fields.Char('Ambiente')
#    x_tipo_emision = fields.Char('TIpo de Emisión')
    x_ret_clave_acceso = fields.Char('Clave de Acceso Ret.', required=False)
    x_ret_codigo_documento = fields.Char('Código de Documento - Ret. Elec', required=False)
    x_ret_fecha_emision = fields.Date('Fecha Retención', required=False)
# Campos Forma de Pago
    x_forma_pago_id = fields.One2many('forma.pago.line', 'invoice_id', string='Transacción', copy=True)

    @api.one
    @api.depends('number')
    def _compute_establecimiento(self):
        if self.number:
            self.x_company_establecimiento = self.number[0:3]

    @api.one
    @api.depends('number')
    def _compute_emision(self):
        if self.number:
            self.x_company_emision = self.number[4:7]

    @api.one
    @api.depends('number')
    def _compute_secuencial(self):
        if self.number:
            self.x_company_secuencial = self.number[8:17]

    @api.one
    @api.depends('tax_line_ids.amount')
    def _compute_impuesto(self):
        self.x_impuesto = sum([line.amount for line in self.tax_line_ids if line.amount >= 0.0])

class FormaPagoLine(models.Model):
    _name = 'forma.pago.line'
    name = fields.Many2one('forma.pago', 'Transacción')
    invoice_id = fields.Many2one('account.invoice', string='Invoice Reference',
        ondelete='cascade', index=True)

    _sql_constraints = [
        ('name_invoice_uniq', 'unique (name,invoice_id)', 'El método de pago no puede repetirse!')
    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: