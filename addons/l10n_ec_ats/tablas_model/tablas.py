# -*- coding: utf-8 -*-

from openerp import models, fields, api

#class res_partner(models.Model):
#    _inherit = 'res.partner'
#    x_tipoid = fields.Char('Tipo Identificación', help="Ingrese el tipo de identificación", required=True)
#    x_id = fields.Char('Número Identificación', help="Ingrese el número de identificación", required=True)

class TipoIdentificacion(models.Model):
    _name = 'tipo.identificacion'
    name = fields.Char('Código', required=True)
    description = fields.Char('Tipo de Identificación', required=True)
    type = fields.Many2one('tipo.transaccion', required=False)

    @api.multi
    @api.depends('name', 'description')
    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.description:
                name = name + ' - ' + record.description
            result.append((record.id, name))
        return result

class TipoSustento(models.Model):
    _name = 'tipo.sustento'
    name = fields.Char('Código', required=True)
    description = fields.Char('Tipo de Sustento', required=True)
    comprobante = fields.Char('Tipo de Comprobante', required=False)

    @api.multi
    @api.depends('name', 'description')
    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.description:
                name = name + ' - ' + record.description
            result.append((record.id, name))
        return result

class TipoComprobante(models.Model):
    _name = 'tipo.comprobante'
    name = fields.Char('Código', required=True)
    description = fields.Char('Tipo de Comprobante', required=True)

    @api.multi
    @api.depends('name', 'description')
    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.description:
                name = name + ' - ' + record.description
            result.append((record.id, name))
        return result

class TipoTransaccion(models.Model):
    _name = 'tipo.transaccion'
    name = fields.Char('Código', required=True)
    description = fields.Char('Tipo de Transacción', required=True)

    @api.multi
    @api.depends('name', 'description')
    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.description:
                name = name + ' - ' + record.description
            result.append((record.id, name))
        return result

class IdentificacionRef(models.Model):
    _name = 'identificacion.referencial'
    name = fields.Char('Código', required=True)
    description = fields.Char('Identificación Referencial', required=True)

    @api.multi
    @api.depends('name', 'description')
    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.description:
                name = name + ' - ' + record.description
            result.append((record.id, name))
        return result

class CodigoRetencion(models.Model):
    _name = 'codigo.retencion'
    name = fields.Char('Código', required=True)
    description = fields.Char('Concepto de Retención', required=True)

    @api.multi
    @api.depends('name', 'description')
    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.description:
                name = name + ' - ' + record.description
            result.append((record.id, name))
        return result