from odoo import fields, models, api, exceptions, _

class RegistrarAvance(models.TransientModel):
    _name = "registrar.avance.wizard"
    _description = "Registrar Avance Wizard"

    id = fields.Integer(string='ID')
    fecha = fields.Date(string='Fecha')
    avance = fields.Integer(string='Avance')
    archivos = fields.Many2many(comodel_name='ir.attachment', string='Subir Archivo')
    nombres_archivos = fields.Char(string='Nombres de Archivos')
    comentarios = fields.Text(string='Comentarios')

    def action_confirm(self):
        # Lógica del wizard aquí
        # Puedes añadir cualquier lógica adicional que necesites
        print("Wizard confirmed")
