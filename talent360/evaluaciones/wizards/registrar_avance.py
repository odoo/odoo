from odoo import fields, models, api, exceptions, _

class RegistrarAvance(models.TransientModel):
    _name = "registrar.avance.wizard"
    _description = "Registrar Avance Wizard"

    fecha = fields.Date(string='Fecha', default=fields.Date.today())
    avance = fields.Integer(string='Avance')
    archivos = fields.Many2many(comodel_name='ir.attachment', string='Subir Archivo')
    nombres_archivos = fields.Char(string='Nombres de Archivos')
    comentarios = fields.Text(string='Comentarios')

    def action_confirm(self):
        avance = self.avance
        archivos = self.archivos
        comentarios = self.comentarios
        fecha = self.fecha

        message = f"ID: {self.id}\nFecha: {fecha}\nAvance: {avance}\nArchivos: {', '.join(archivos.mapped('name'))}\nComentarios: {comentarios}"
        
        print(message)
