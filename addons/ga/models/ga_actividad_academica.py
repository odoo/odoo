from odoo import fields, models
class ActividadAcademica(models.Model):
    _name="ga.actividad.academica"
    _description="ActividadAcademica"
    codigo=fields.Char(required=True)
    descripcion=fields.Text()
    fecha_registro=fields.Datetime()
    fecha_entrega=fields.Datetime()
    ponderacion=fields.Float()
    paralelo_profesor_id = fields.Many2one("ga.paralelo.profesor", string="ParaleloProfesor", required=True)
    ciclo_academico_id = fields.Many2one("ga.ciclo.academico", string="CicloAcademico", required=True)
    