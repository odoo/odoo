from odoo import models, fields, api


class Grupo(models.Model):
    _name = 'hr.schedule.grupo'
    _description = 'Team/Group of Auxiliares'

    _code_uniq = models.Constraint(
        'UNIQUE(code)',
        'Team Code must be unique.',
    )

    name = fields.Char('Team Name', required=True)
    code = fields.Char('Team Code')
    descripcion = fields.Text('Description')

    auxiliar_ids = fields.Many2many(
        'hr.schedule.auxiliar',
        'auxiliar_grupo_rel',
        'grupo_id',
        'auxiliar_id',
        'Members'
    )

    cantidad_miembros = fields.Integer(
        'Member Count',
        compute='_compute_cantidad_miembros',
        store=True
    )

    @api.depends('auxiliar_ids')
    def _compute_cantidad_miembros(self):
        for record in self:
            record.cantidad_miembros = len(record.auxiliar_ids)