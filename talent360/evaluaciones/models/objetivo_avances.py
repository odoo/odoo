from odoo import fields, models, api, exceptions, _

class ObjetivoAvance(models.Model):
    _name = "objetivo.avances"
    _description = "Objetivo Avance"

    objetivo_id = fields.Many2one('objetivo', string='Objetivo', required=True)
    fecha = fields.Date(string='Fecha', required=True)
    avance = fields.Integer(string='Avance', required=True)
    comentarios = fields.Text(string='Comentarios')
    archivos = fields.Many2many(comodel_name='ir.attachment', string='Archivos')
    