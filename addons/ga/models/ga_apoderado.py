from odoo import models, fields

class Apoderado(models.Model):
    _name = 'ga.apoderado'
    _description = 'Modelo para los Tutores'

    codigo = fields.Integer()
    ci = fields.Integer()
    nombre = fields.Text()
    fecha_nacimiento = fields.Date()
    ocupacion = fields.Text()
    domicilio = fields.Text()
    telefono = fields.Integer()
    parentesco = fields.Text()
    token = fields.Text()
