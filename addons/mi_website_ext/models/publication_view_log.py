# mi_website_ext/models/publication_view_log.py
from odoo import models, fields

class PublicationViewLog(models.Model):
    _name = 'publication.view.log'
    _description = 'Registro de Vistas de Publicaciones'
    _order = 'create_date desc'

    # El objeto que fue visto (puede ser una publicación, política, etc.)
    res_model = fields.Char(string='Modelo', required=True, readonly=True, index=True)
    res_id = fields.Integer(string='ID del Registro', required=True, readonly=True, index=True)

    # El usuario que lo vio
    user_id = fields.Many2one('res.users', string='Usuario', required=True, readonly=True, ondelete='cascade')

    # Restricción para asegurar que un usuario solo pueda tener un registro de "visto" por objeto
    _sql_constraints = [
        ('user_object_uniq', 'unique(user_id, res_model, res_id)', 'Este objeto ya ha sido marcado como visto por este usuario.')
    ]