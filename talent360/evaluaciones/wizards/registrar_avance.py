from odoo import fields, models, api, exceptions, _

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
        usuario_objetivo = self.env["objetivo"].browse(objetivo_id)
        
        self.env["objetivo.avances"].create({
            "objetivo_id": usuario_objetivo.id,
            "fecha": fecha,
            "avance": avance,
            "comentarios": comentarios,
            "archivos": [(6, 0, archivos.ids)],
        })
        
        usuario_objetivo.sudo().write({"resultado": avance})
        