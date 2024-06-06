from odoo import fields, models
class RutaChofer(models.Model):
    _name="ga.ruta.chofer"
    _description="Ruta del Chofer"

    chofer_id=fields.Many2one("ga.chofer", string="Chofer",required=True)
    alumno_id=fields.Many2one("ga.alumno", string="Alumno",required=True)
    ruta_id=fields.Many2one("ga.ruta", string="Ruta",required=True)
