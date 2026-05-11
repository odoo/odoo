from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Servicio(models.Model):
    _name = 'hr.schedule.servicio'
    _description = 'Service Assignment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Service ID', readonly=True)
    cliente_id = fields.Many2one('hr.schedule.cliente', 'Client', required=True)
    grupo_id = fields.Many2one('hr.schedule.grupo', 'Team')
    auxiliar_ids = fields.Many2many('hr.schedule.auxiliar', 'servicio_auxiliar_rel', 'servicio_id', 'auxiliar_id', 'Auxiliares')

    fecha_servicio = fields.Date('Service Date', required=True)
    hora_inicio = fields.Float('Start Time', required=True)
    hora_fin = fields.Float('End Time', required=True)

    direccion = fields.Char('Service Address', required=True)
    anotaciones = fields.Text('Notes/Special Instructions')

    estado_id = fields.Selection([
        ('programada', 'Scheduled'),
        ('en_curso', 'In Progress'),
        ('completada', 'Completed'),
        ('cancelada', 'Cancelled'),
        ('disputa', 'In Dispute'),
    ], 'Status', default='programada', tracking=True)

    created_by_id = fields.Many2one('res.users', 'Created By', readonly=True)

    periodo_anio_mes = fields.Char('Period YYYY-MM', compute='_compute_periodo', store=True)
    periodo_quincena = fields.Selection(
        [('q1', 'Primera quincena'), ('q2', 'Segunda quincena')],
        'Quincena',
        compute='_compute_periodo',
        store=True
    )

    @api.depends('fecha_servicio')
    def _compute_periodo(self):
        for record in self:
            if record.fecha_servicio:
                fecha = record.fecha_servicio
                record.periodo_anio_mes = f"{fecha.year:04d}-{fecha.month:02d}"
                record.periodo_quincena = 'q1' if fecha.day <= 15 else 'q2'
            else:
                record.periodo_anio_mes = False
                record.periodo_quincena = False

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env['ir.sequence']
        for vals in vals_list:
            vals['name'] = sequence.next_by_code('hr.schedule.servicio') or 'SRV-NEW'
            vals['created_by_id'] = self.env.uid
        records = super().create(vals_list)
        records._run_operational_validations()
        records._sync_service_sessions()
        return records

    def write(self, vals):
        before_map = {rec.id: rec.auxiliar_ids.mapped('name') for rec in self} if 'auxiliar_ids' in vals else {}
        res = super().write(vals)
        self._run_operational_validations()
        self._sync_service_sessions()

        if 'auxiliar_ids' in vals:
            for rec in self:
                before = ', '.join(before_map.get(rec.id, [])) or '-'
                after = ', '.join(rec.auxiliar_ids.mapped('name')) or '-'
                if before != after:
                    rec.message_post(body=f"Reasignación de auxiliares: {before} → {after}")
        return res

    @api.constrains('hora_inicio', 'hora_fin')
    def _check_horas(self):
        for record in self:
            if record.hora_inicio >= record.hora_fin:
                raise ValidationError('Start time must be before end time')

    def _run_operational_validations(self):
        for record in self:
            record._check_horas()
            record._validate_assignment()

    def _validate_assignment(self):
        for record in self:
            for aux in record.auxiliar_ids:
                if aux.estado_id != 'activo':
                    raise ValidationError(f'Cannot assign {aux.name}: status is not active.')
            record._check_auxiliar_active_novedades()
            record._check_cliente_limit()

    def _check_auxiliar_active_novedades(self):
        novedad_model = self.env['hr.schedule.novedad']
        for record in self:
            if not record.fecha_servicio:
                continue
            for aux in record.auxiliar_ids:
                novedad = novedad_model.search([
                    ('auxiliar_id', '=', aux.id),
                    ('estado_id', '=', 'activa'),
                    ('fecha_inicio', '<=', record.fecha_servicio),
                    '|', ('fecha_fin', '=', False), ('fecha_fin', '>=', record.fecha_servicio),
                ], limit=1)
                if novedad:
                    raise ValidationError(
                        f'Cannot assign {aux.name}: active novelty ({novedad.tipo_novedad}) on service date.'
                    )

    @api.constrains('auxiliar_ids', 'fecha_servicio', 'hora_inicio', 'hora_fin', 'estado_id')
    def _check_solapamiento(self):
        for record in self:
            if record.estado_id == 'cancelada' or not record.auxiliar_ids or not record.fecha_servicio:
                continue

            overlaps = self.search([
                ('id', '!=', record.id),
                ('estado_id', '!=', 'cancelada'),
                ('fecha_servicio', '=', record.fecha_servicio),
                ('hora_inicio', '<', record.hora_fin),
                ('hora_fin', '>', record.hora_inicio),
                ('auxiliar_ids', 'in', record.auxiliar_ids.ids),
            ], limit=1)

            if overlaps:
                conflicted_aux = (record.auxiliar_ids & overlaps.auxiliar_ids).mapped('name')
                raise ValidationError(
                    'Time overlap detected for: %s (service %s).' % (
                        ', '.join(conflicted_aux) or 'auxiliar',
                        overlaps.display_name,
                    )
                )
    def _check_cliente_limit(self):
        for record in self:
            if not record.grupo_id:
                continue
            servicios_dia = self.search([
                ('id', '!=', record.id),
                ('grupo_id', '=', record.grupo_id.id),
                ('fecha_servicio', '=', record.fecha_servicio),
                ('estado_id', 'not in', ['cancelada']),
            ])
            clientes_ids = set(servicios_dia.mapped('cliente_id').ids)
            clientes_ids.add(record.cliente_id.id)
            if len(clientes_ids) > 3:
                raise ValidationError('Group cannot serve more than 3 clients per day.')

    def _sync_service_sessions(self):
        session_model = self.env['hr.schedule.service.session']
        for record in self:
            existing_sessions = session_model.search([('servicio_id', '=', record.id)])
            existing_aux_ids = set(existing_sessions.mapped('auxiliar_id').ids)
            target_aux_ids = set(record.auxiliar_ids.ids)

            # Crear sesiones faltantes
            missing_aux_ids = target_aux_ids - existing_aux_ids
            for aux_id in missing_aux_ids:
                session_model.create({
                    'servicio_id': record.id,
                    'auxiliar_id': aux_id,
                })

            # Eliminar sesiones no iniciadas de auxiliares removidos
            removable_sessions = existing_sessions.filtered(
                lambda s: s.auxiliar_id.id not in target_aux_ids and s.estado_id == 'no_iniciada'
            )
            if removable_sessions:
                removable_sessions.unlink()

    


class ServicioAuxiliar(models.Model):
    _name = 'hr.schedule.servicio.auxiliar'
    _description = 'Service-Auxiliar Assignment'

    servicio_id = fields.Many2one('hr.schedule.servicio', 'Service', ondelete='cascade')
    auxiliar_id = fields.Many2one('hr.schedule.auxiliar', 'Auxiliar', ondelete='cascade')