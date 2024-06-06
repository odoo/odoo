from odoo import models, fields

class Alumno(models.Model):
    _name = 'ga.alumno'
    _description = 'Modelo para los Alumnos'

    codigo = fields.Integer()
    ci = fields.Integer()
    nombre = fields.Text()
    fecha_nacimiento = fields.Date()
    genero = fields.Text()
    nacionalidad = fields.Text()
    domicilio = fields.Text()
    telefono = fields.Integer()
    correo = fields.Text()
    token = fields.Text()
    latitud = fields.Float()
    longitud = fields.Float()