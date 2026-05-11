from odoo import models, fields, api
from datetime import datetime

class Novedad(models.Model):
    _name = 'hr.schedule.novedad'
    _description = 'Incident/Novelty Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Novelty Id', readonly=True)
    auxiliar_id = fields.Many2one('hr.schedule.auxiliar', 'Auxiliar', required=True, tracking=True)
    
    tipo_novedad = fields.Selection([
        ('accidente', 'Accident/Injury'),
        ('enfermedad', 'Illness'),
        ('licencia', 'Leave'),
        ('retraso', 'Delay'),
        ('no_presentacion', 'No-Show'),
        ('liquidacion', 'Termination'),
    ], 'Type', required=True, tracking=True)
    
    fecha_inicio = fields.Date('Start Date', default=fields.Date.today, required=True)
    fecha_fin = fields.Date('End Date')
    estado_id = fields.Selection([
        ('activa', 'Active'),
        ('vencida', 'Expired'),
        ('resuelta', 'Resolved'),
    ], 'Status', default='activa', tracking=True)
    
    descripcion = fields.Text('Description')
    archivo_soporte = fields.Binary('Support File')
    
    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env['ir.sequence']
        for vals in vals_list:
            vals['name'] = sequence.next_by_code('hr.schedule.novedad') or 'NOV-NEW'
        return super().create(vals_list)