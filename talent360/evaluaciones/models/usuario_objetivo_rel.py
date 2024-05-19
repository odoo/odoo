from odoo import models, fields


class UsuarioObjetivoRel(models.Model):
    """
    Modelo para representar la relación entre usuarios y objetivos
        
    :param _name(str): Nombre del modelo en Odoo
    :param _description (str): Descripción del modelo en Odoo
    :param evaluacion_id = Identificador de la evaluación
    :param objetivo_id = Identificador del objetivo
    """

    _name = "usuario.objetivo.rel"
    _description = "Relación entre objetivos y usuarios"

    objetivo_id = fields.Many2one("objetivo", string="Objetivos")
    usuario_id = fields.Many2one("res.users", string="Usuario")

    titulo = fields.Char(related='objetivo_id.titulo', string="Título del Objetivo")
    fecha_fin = fields.Date(related='objetivo_id.fecha_fin', string="Fecha Fin")
    tipo = fields.Selection(related='objetivo_id.tipo', string="Tipo")
    estado = fields.Selection(related='objetivo_id.estado', string="Estado")
    peso = fields.Integer(related='objetivo_id.peso', string="Peso")
    piso_minimo = fields.Integer(related='objetivo_id.piso_minimo', string="Piso Mínimo")
    piso_maximo = fields.Integer(related='objetivo_id.piso_maximo', string="Piso Máximo")

    def open_objetivo_form(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'objetivo',
            'view_mode': 'form',
            'res_id': self.objetivo_id.id,
        }
