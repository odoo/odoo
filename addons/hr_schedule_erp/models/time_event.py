from odoo import models, fields, api
from odoo.exceptions import ValidationError


class TimeEvent(models.Model):
    _name = 'hr.schedule.time.event'
    _description = 'Time Capture Event (Check-in/Out)'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Event ID', readonly=True)

    service_session_id = fields.Many2one('hr.schedule.service.session', 'Session', required=True, ondelete='cascade')
    auxiliar_id = fields.Many2one('hr.schedule.auxiliar', 'Auxiliar', related='service_session_id.auxiliar_id', store=True)

    tipo_evento = fields.Selection([
        ('check_in', 'Check-In'),
        ('check_out', 'Check-Out'),
    ], 'Event Type', required=True)

    timestamp_dispositivo = fields.Datetime('Device Timestamp')
    timestamp_servidor = fields.Datetime('Server Timestamp', readonly=True)

    ubicacion_gps = fields.Char('GPS Location (optional)')
    evidencia_foto = fields.Binary('Evidence Photo (optional)')

    sincronizado = fields.Boolean('Synced to Server', default=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.schedule.time.event') or 'EVT-NEW'
            vals['timestamp_servidor'] = fields.Datetime.now()

        records = super().create(vals_list)
        for record in records:
            record._validate_event_sequence()
        return records

    def _validate_event_sequence(self):
        self.ensure_one()
        session = self.service_session_id

        if self.tipo_evento == 'check_in':
            other = self.search_count([
                ('id', '!=', self.id),
                ('service_session_id', '=', session.id),
                ('tipo_evento', '=', 'check_in'),
            ])
            if other > 0:
                raise ValidationError('Only one check-in event is allowed per session.')

        if self.tipo_evento == 'check_out':
            has_checkin = self.search_count([
                ('service_session_id', '=', session.id),
                ('tipo_evento', '=', 'check_in'),
            ]) > 0
            if not has_checkin:
                raise ValidationError('Cannot create check-out without an existing check-in.')