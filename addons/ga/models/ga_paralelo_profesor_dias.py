from odoo import fields, models
class Dias(models.Model):
    _name="ga.dias"
    _description="Dias"
    codigo= fields.Char(required=True, string="Código")
    descripcion = fields.Char(required=True, string="Dias")
    abreviatura = fields.Char(required=True, string="Abreviatura")

class ParaleloProfesorDias(models.Model):
    _name="ga.paralelo.profesor.dias"
    _description="Paralelo profesor dias"
    hora_inicio=fields.Float(string="Hora de Inicio")
    duracion=fields.Integer(string="Duracion Clase")
    dias_id= fields.Many2one("ga.dias", required=True, string="Dias")
    paralelo_profesor_id=fields.Many2one("ga.paralelo.profesor", required=True, string="Paralelo Profesor")