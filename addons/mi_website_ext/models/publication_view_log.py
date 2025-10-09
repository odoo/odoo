# mi_website_ext/models/publication_view_log.py
from odoo import api, models, fields

class PublicationViewLog(models.Model):
    _name = 'publication.view.log'
    _description = 'Registro de Vistas de Publicaciones'
    _order = 'create_date desc'

    res_model = fields.Char(string='Modelo', required=True, readonly=True, index=True)
    res_id = fields.Integer(string='ID del Registro', required=True, readonly=True, index=True)
    user_id = fields.Many2one('res.users', string='Usuario', required=True, readonly=True, ondelete='cascade')

    employee_id = fields.Many2one(
        'hr.employee', string="Empleado",
        related='user_id.employee_id',
        store=True,  
        readonly=True
    )

   
    _sql_constraints = [
        ('user_object_uniq', 'unique(user_id, res_model, res_id)', 'Este objeto ya ha sido marcado como visto por este usuario.')
    ]

    @api.depends('res_model', 'res_id')
    def _compute_publication_name(self):
        for log in self:
            if log.res_model == 'website.publication' and log.res_id:
                publication = self.env['website.publication'].browse(log.res_id).exists()
                log.publication_name = publication.name if publication else 'Registro no encontrado'
            else:
                log.publication_name = ''


    def open_view_wizard_from_log(self):
        self.ensure_one()
        if self.res_model == 'website.publication':
            return {
                'type': 'ir.actions.act_window',
                'name': 'Ver Seguimiento de Lectura',
                'res_model': 'publication.view.wizard',
                'view_mode': 'form',
                'view_id': self.env.ref('mi_website_ext.view_publication_view_wizard_form').id,
                'target': 'new',
                'context': {
                    'default_publication_id': self.res_id,
                }
            }
