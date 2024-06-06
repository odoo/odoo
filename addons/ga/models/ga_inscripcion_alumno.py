from odoo import models, fields

class InscripcionAlumno(models.Model):
    _name = 'ga.incripcion.alumno'
    _description = 'Modelo para la inscripcion de alumnos'

    gestion_id = fields.Many2one("ga.gestion", string="Gestion",required=True)
    grado_id = fields.Many2one("ga.grado", string="Grado",required=True)
    paralelo_id = fields.Many2one("ga.Paralelo", string="Paralelo",required=True)
    apoderado_id = fields.Many2one("ga.apoderado", string="Apoderado",required=True)
    alumno_id = fields.Many2one("ga.alumno", string="Alumno",required=True)

