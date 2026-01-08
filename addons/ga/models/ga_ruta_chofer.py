from odoo import fields, models
class RutaChofer(models.Model):
    _name="ga.ruta.chofer"
    _description="Ruta del Chofer"

    chofer_id=fields.Many2one("hr.employee", required=True)
    alumno_id=fields.Many2one("ga.alumno", required=True)
    ruta_id=fields.Many2one("ga.ruta", required=True)
