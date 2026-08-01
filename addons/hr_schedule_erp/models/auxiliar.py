from odoo import models, fields, api
from odoo.exceptions import ValidationError  # <- agregar

class Auxiliar(models.Model):
    _name = 'hr.schedule.auxiliar'
    _description = 'Support Personnel (Auxiliar)'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _cedula_uniq = models.Constraint(
        'UNIQUE(cedula)',
        'ID Number must be unique.',
    )

    name = fields.Char('Full Name', required=True, tracking=True)
    cedula = fields.Char('ID Number')
    email = fields.Char('Email')
    phone = fields.Char('Phone')
    
    estado_id = fields.Selection([
        ('activo', 'Active'),
        ('inactivo', 'Inactive'),
        ('liquidacion', 'Under Liquidation'),
        ('licencia', 'On Leave'),
        ('accidente', 'Accident/Injured'),
        ('enfermedad', 'Illness'),
    ], 'Status', default='activo', required=True, tracking=True)
    
    grupo_ids = fields.Many2many('hr.schedule.grupo', 'auxiliar_grupo_rel', 'auxiliar_id', 'grupo_id', 'Teams')
    
    documentacion_vigente = fields.Boolean('Current Security Docs?', default=False)
    fecha_vencimiento_docs = fields.Date('Doc Expiry Date')
    
    servicio_ids = fields.One2many('hr.schedule.servicio.auxiliar', 'auxiliar_id', 'Assigned Services')
    
    puede_editar_programacion = fields.Boolean('Can Edit Schedule?', default=False)
    
    def _get_estado_display(self):
        return dict(self._fields['estado_id'].selection).get(self.estado_id, 'Unknown')

    @api.constrains('cedula')
    def _check_cedula_format(self):
        for record in self:
            if record.cedula and not record.cedula.isdigit():
                raise ValidationError('ID must contain only numbers')