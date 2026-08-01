from odoo import models, fields, api
from odoo.exceptions import ValidationError


class DisputeCase(models.Model):
    _name = 'hr.schedule.dispute.case'
    _description = 'Dispute Case (Time Discrepancy)'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Case ID', readonly=True)

    service_session_id = fields.Many2one('hr.schedule.service.session', 'Session', required=True, ondelete='cascade')
    auxiliar_id = fields.Many2one('hr.schedule.auxiliar', 'Auxiliar', related='service_session_id.auxiliar_id', store=True)
    cliente_id = fields.Many2one('hr.schedule.cliente', 'Client', related='service_session_id.cliente_id', store=True)

    horas_erp = fields.Float('Hours Recorded (ERP)', required=True)
    horas_cliente = fields.Float('Hours Recognized (Client)')
    diferencia = fields.Float('Difference (hours)', compute='_compute_diferencia', store=True)

    tipo_discrepancia = fields.Selection([
        ('duracion_menor', 'Client Reports Shorter Duration'),
        ('duracion_mayor', 'Client Reports Longer Duration'),
        ('no_presentacion', 'No-Show by Client'),
        ('error_captura', 'Capture Error'),
    ], 'Discrepancy Type', required=True, tracking=True)

    resolucion_id = fields.Selection([
        ('acepta_erp', 'Accept ERP Hours'),
        ('acepta_cliente', 'Accept Client Hours'),
        ('acuerdo_promedio', 'Split Difference'),
        ('revision_manual', 'Requires Manual Review'),
    ], 'Resolution', tracking=True)

    motivo_resolucion = fields.Text('Resolution Reason')
    resuelto_por_id = fields.Many2one('res.users', 'Resolved By', tracking=True)
    fecha_resolucion = fields.Datetime('Resolution Date', tracking=True)

    estado_id = fields.Selection([
        ('abierta', 'Open'),
        ('en_revision', 'Under Review'),
        ('resuelta', 'Resolved'),
    ], 'Status', default='abierta', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.schedule.dispute.case') or 'DSP-NEW'
        return super().create(vals_list)

    @api.depends('horas_erp', 'horas_cliente')
    def _compute_diferencia(self):
        for record in self:
            record.diferencia = abs((record.horas_erp or 0.0) - (record.horas_cliente or 0.0))

    def action_mark_review(self):
        for record in self:
            if record.estado_id == 'resuelta':
                raise ValidationError('Resolved disputes cannot return to review.')
            record.estado_id = 'en_revision'

    def action_resolve(self):
        for record in self:
            if not record.resolucion_id:
                raise ValidationError('Select a resolution before closing the dispute.')
            record.resuelto_por_id = self.env.user.id
            record.fecha_resolucion = fields.Datetime.now()
            record.estado_id = 'resuelta'