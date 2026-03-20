from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ReasignacionWizard(models.TransientModel):
    _name = 'hr.schedule.reasignacion.wizard'
    _description = 'Reasignación Rápida de Auxiliares'

    servicio_id = fields.Many2one('hr.schedule.servicio', 'Servicio', required=True)
    auxiliar_origen_id = fields.Many2one('hr.schedule.auxiliar', 'Auxiliar origen', required=True)
    auxiliar_destino_id = fields.Many2one('hr.schedule.auxiliar', 'Auxiliar reemplazo', required=True)

    motivo = fields.Selection([
        ('accidente', 'Accidente de trayecto'),
        ('enfermedad', 'Enfermedad'),
        ('cambio_cliente', 'Cambio solicitado por cliente'),
        ('otro', 'Otro'),
    ], 'Motivo', required=True)

    detalle_motivo = fields.Text('Detalle', required=True)

    @api.onchange('servicio_id')
    def _onchange_servicio_id(self):
        if self.servicio_id:
            return {
                'domain': {
                    'auxiliar_origen_id': [('id', 'in', self.servicio_id.auxiliar_ids.ids)],
                    'auxiliar_destino_id': [('estado_id', '=', 'activo'), ('id', 'not in', self.servicio_id.auxiliar_ids.ids)],
                }
            }
        return {}

    def action_confirmar(self):
        self.ensure_one()

        if self.auxiliar_origen_id == self.auxiliar_destino_id:
            raise ValidationError('El auxiliar de origen y destino no pueden ser el mismo.')

        servicio = self.servicio_id
        if self.auxiliar_origen_id not in servicio.auxiliar_ids:
            raise ValidationError('El auxiliar de origen no está asignado al servicio.')

        nuevos_auxiliares = (servicio.auxiliar_ids - self.auxiliar_origen_id) | self.auxiliar_destino_id
        servicio.write({'auxiliar_ids': [(6, 0, nuevos_auxiliares.ids)]})

        servicio.message_post(
            body=(
                f"Reasignación rápida realizada. "
                f"Motivo: {self.motivo}. "
                f"Origen: {self.auxiliar_origen_id.name}. "
                f"Destino: {self.auxiliar_destino_id.name}. "
                f"Detalle: {self.detalle_motivo}"
            )
        )

        return {'type': 'ir.actions.act_window_close'}