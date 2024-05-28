from odoo import fields, models, api, exceptions, _
from odoo.http import request

class RegistrarAvance(models.TransientModel):
    _name = "registrar.avance.wizard"
    _description = "Registrar Avance Wizard"

    fecha = fields.Date(string='Fecha', default=fields.Date.today())
    avance = fields.Integer(string='Avance', required=True)
    archivos = fields.Many2many(comodel_name='ir.attachment', string='Subir Archivo')
    nombres_archivos = fields.Char(string='Nombres de Archivos')
    comentarios = fields.Text(string='Comentarios')

    def action_confirmar(self):
        avance = self.avance
        archivos = self.archivos
        comentarios = self.comentarios
        fecha = self.fecha
        
        objetivo_id = self.env.context.get("objetivo_id")
        usuario_objetivo_model = self.env["objetivo"].browse(objetivo_id)
        usuario_objetivo_model.sudo().write({"resultado": avance})

        message = f"ID: {self.id}\nFecha: {fecha}\nAvance: {avance}\nArchivos: {', '.join(archivos.mapped('name'))}\nComentarios: {comentarios}"
        
        print(message)
