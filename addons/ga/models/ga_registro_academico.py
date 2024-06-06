from odoo import fields, models

class RegistroAcademico(models.Model):
    _name = "ga.registro.academico"
    _description = "GA Registro Academico"

    fecha_entrega = fields.Datetime()
    calificacion = fields.Float()
    alumno_id = fields.Many2one("ga.alumno", string="Alumno",required=True)
    actividad_academica_id = fields.Many2one("ga.actividad.academica", string="ActividadAcademica",required=True)