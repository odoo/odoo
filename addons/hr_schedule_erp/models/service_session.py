from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ServiceSession(models.Model):
    _name = 'hr.schedule.service.session'
    _description = 'Service Session (Daily Work)'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Session ID', readonly=True)

    servicio_id = fields.Many2one('hr.schedule.servicio', 'Service Assignment', required=True, ondelete='cascade')
    auxiliar_id = fields.Many2one('hr.schedule.auxiliar', 'Auxiliar', required=True, tracking=True)
    cliente_id = fields.Many2one('hr.schedule.cliente', 'Client', related='servicio_id.cliente_id', store=True)

    fecha = fields.Date('Session Date', related='servicio_id.fecha_servicio', store=True)
    hora_inicio_programada = fields.Float('Scheduled Start Time', related='servicio_id.hora_inicio', store=True)
    hora_fin_programada = fields.Float('Scheduled End Time', related='servicio_id.hora_fin', store=True)

    check_in_time = fields.Datetime('Actual Check-In', tracking=True)
    check_out_time = fields.Datetime('Actual Check-Out', tracking=True)

    estado_id = fields.Selection([
        ('no_iniciada', 'Not Started'),
        ('en_curso', 'In Progress'),
        ('finalizada', 'Completed'),
        ('cancelada', 'Cancelled'),
    ], 'Status', default='no_iniciada', tracking=True)

    firma_cliente = fields.Binary('Client Signature')
    confirmacion_cliente = fields.Text('Client Confirmation/Notes')
    horas_cliente_reportadas = fields.Float('Client Recognized Hours')

    time_event_ids = fields.One2many('hr.schedule.time.event', 'service_session_id', 'Time Events')
    horas_trabajadas = fields.Float('Worked Hours', compute='_compute_horas_trabajadas', store=True)

    def write(self, vals):
        res = super().write(vals)
        trigger_fields = {'horas_cliente_reportadas', 'check_in_time', 'check_out_time'}
        if trigger_fields.intersection(vals.keys()):
            for record in self:
                record._create_dispute_if_needed()
                record._refresh_parent_service_status()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.schedule.service.session') or 'SES-NEW'
        return super().create(vals_list)

    @api.depends('check_in_time', 'check_out_time')
    def _compute_horas_trabajadas(self):
        for record in self:
            if record.check_in_time and record.check_out_time:
                delta = record.check_out_time - record.check_in_time
                record.horas_trabajadas = delta.total_seconds() / 3600.0
            else:
                record.horas_trabajadas = 0.0

    def _has_client_evidence(self):
        self.ensure_one()
        return bool(self.confirmacion_cliente or self.firma_cliente)

    def action_check_in(self):
        for record in self:
            if record.estado_id == 'cancelada':
                raise ValidationError('Cannot check-in a cancelled session.')
            if record.check_in_time and not record.check_out_time:
                raise ValidationError('Session already checked in and still in progress.')
            if record.check_in_time and record.check_out_time:
                raise ValidationError('Session is already completed.')

            now = fields.Datetime.now()
            record.check_in_time = now
            record.estado_id = 'en_curso'

            self.env['hr.schedule.time.event'].create({
                'service_session_id': record.id,
                'tipo_evento': 'check_in',
                'timestamp_dispositivo': now,
                'sincronizado': True,
            })

            if record.servicio_id:
                record.servicio_id.estado_id = 'en_curso'

    def action_check_out(self):
        for record in self:
            if record.estado_id == 'cancelada':
                raise ValidationError('Cannot check-out a cancelled session.')
            if not record.check_in_time:
                raise ValidationError('Cannot check-out without check-in.')
            if record.check_out_time:
                raise ValidationError('Session already checked out.')
            if not record._has_client_evidence():
                raise ValidationError('Client confirmation/signature is required to close session.')

            now = fields.Datetime.now()
            record.check_out_time = now
            record.estado_id = 'finalizada'

            self.env['hr.schedule.time.event'].create({
                'service_session_id': record.id,
                'tipo_evento': 'check_out',
                'timestamp_dispositivo': now,
                'sincronizado': True,
            })

            record._create_dispute_if_needed()
            record._refresh_parent_service_status()

    def _create_dispute_if_needed(self):
        self.ensure_one()

        if not self.check_in_time or not self.check_out_time:
            return

        if self.horas_cliente_reportadas in (False, None):
            return

        erp_hours = (self.check_out_time - self.check_in_time).total_seconds() / 3600.0
        client_hours = float(self.horas_cliente_reportadas or 0.0)
        diff = abs(erp_hours - client_hours)

        if diff < 0.01:
            return

        dispute_model = self.env['hr.schedule.dispute.case']
        existing_open = dispute_model.search([
            ('service_session_id', '=', self.id),
            ('estado_id', 'in', ['abierta', 'en_revision']),
        ], limit=1)
        if existing_open:
            return

        tipo = 'duracion_menor' if client_hours < erp_hours else 'duracion_mayor'
        dispute_model.create({
            'service_session_id': self.id,
            'horas_erp': erp_hours,
            'horas_cliente': client_hours,
            'tipo_discrepancia': tipo,
            'estado_id': 'abierta',
        })
    def _refresh_parent_service_status(self):
        self.ensure_one()
        if not self.servicio_id:
            return

        service = self.servicio_id
        sessions = self.search([('servicio_id', '=', service.id)])

        has_open_dispute = self.env['hr.schedule.dispute.case'].search_count([
            ('service_session_id', 'in', sessions.ids),
            ('estado_id', 'in', ['abierta', 'en_revision']),
        ]) > 0

        if has_open_dispute:
            service.estado_id = 'disputa'
            return

        states = sessions.mapped('estado_id')
        if states and all(state in ['finalizada', 'cancelada'] for state in states):
            service.estado_id = 'completada'
        elif 'en_curso' in states:
            service.estado_id = 'en_curso'
        else:
            service.estado_id = 'programada'