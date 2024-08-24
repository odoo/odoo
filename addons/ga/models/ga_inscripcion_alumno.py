from odoo import models, fields

class InscripcionAlumno(models.Model):
    _name = 'ga.inscripcion.alumno'
    _description = 'Modelo para la inscripcion de alumnos'

    gestion_id = fields.Many2one("ga.gestion",required=True)
    grado_id = fields.Many2one("ga.grado",required=True)
    paralelo_id = fields.Many2one("ga.paralelo", required=True)
    apoderado_id = fields.Many2one("ga.apoderado", required=True)
    alumno_id = fields.Many2one("ga.alumno", required=True)

