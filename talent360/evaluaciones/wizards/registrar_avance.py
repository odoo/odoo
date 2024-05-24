from odoo import fields, models, api, exceptions, _

class RegistrarAvance(models.TransientModel):
    _name = "registrar.avance.wizard"
    _description = "Registrar Avance Wizard"

    name = fields.Char(string='Name')
    progress = fields.Integer(string='Progress')

    def action_confirm(self):
        # Lógica del wizard aquí
        # Puedes añadir cualquier lógica adicional que necesites
        print("Wizard confirmed")
