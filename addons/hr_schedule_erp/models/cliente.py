from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Cliente(models.Model):
    _name = 'hr.schedule.cliente'
    _description = 'Client'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _code_uniq = models.Constraint(
        'UNIQUE(code)',
        'Client Code must be unique.',
    )

    name = fields.Char('Client Name', required=True, tracking=True)
    code = fields.Char('Client Code')
    email = fields.Char('Email')
    phone = fields.Char('Phone')
    direccion = fields.Char('Address')
    ciudad = fields.Char('City')
    estado_id = fields.Selection([
        ('activo', 'Active'),
        ('inactivo', 'Inactive'),
        ('suspendido', 'Suspended'),
    ], 'Status', default='activo', tracking=True)
    
    servicio_ids = fields.One2many('hr.schedule.servicio', 'cliente_id', 'Services')
    
    es_horario_variable = fields.Boolean('Variable Schedule?', default=False)
    horario_inicio = fields.Float('Start Hour')
    horario_fin = fields.Float('End Hour')
    notas = fields.Text('Notes')
    
    def toggleEstado(self):
        self.estado_id = 'inactivo' if self.estado_id == 'activo' else 'activo'

    @api.constrains('name')
    def _check_name_required(self):
        for record in self:
            if not record.name or record.name.strip() == '':
                raise ValidationError('Client name is required')