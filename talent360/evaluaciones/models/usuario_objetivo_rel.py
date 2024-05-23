from odoo import models, fields, api

class UsuarioObjetivoRel(models.Model):
    """
    Modelo para representar la relación entre usuarios y objetivos

    :param _name(str): Nombre del modelo en Odoo
    :param _description (str): Descripción del modelo en Odoo
    :param evaluacion_id = Identificador de la evaluación
    :param objetivo_id = Identificador del objetivo
    :param titulo (fields.Char): Título del objetivo
    :param titulo (fields.Char): Título del objetivo limitado a 30 caracteres
    :param descripcion (fields.Text): Descrpición del objetivo
    :param descripcion (fields.Text): Descrpición del objetivo limitado a 100 caracteres
    :param resultado(fields.Integer): Resultado del objetivo
    """

    _name = "usuario.objetivo.rel"
    _description = "Relación entre objetivos y usuarios"

    objetivo_id = fields.Many2one("objetivo", string="Objetivos", ondelete="cascade")
    usuario_id = fields.Many2one("res.users", string="Usuario", ondelete="cascade")

    titulo = fields.Char(related="objetivo_id.titulo", string="Título del Objetivo")
    titulo_corto = fields.Char(compute="_compute_kanban")
    descripcion = fields.Text(related="objetivo_id.descripcion")
    descripcion_corta = fields.Char(compute="_compute_kanban")
    resultado = fields.Integer(related="objetivo_id.resultado", string="Resultado")
    
    def abrir_objetivo_form(self):
        """
        Método para que la vista abra el form de objetivos cuando se le hace clic a un objetivo en el kanban de colaboradores
        """
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "objetivo",
            "view_mode": "form",
            "res_id": self.objetivo_id.id,
        }
        
    @api.depends("descripcion", "titulo")
    def _compute_kanban(self):
        """
        Método para agregar elipsis en títulos y descripciones que son mayores a 30 y 100 caracteres respectivamente
        """
        for record in self:
            print(record)
            record.descripcion_corta = record.descripcion[:100] + "..." if len(record.descripcion) > 100 else record.descripcion
            record.titulo_corto = record.titulo[:30] + "..." if len(record.titulo) > 30 else record.titulo
