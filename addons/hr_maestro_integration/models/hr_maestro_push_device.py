# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging

from requests import Session

from odoo import api, fields, models
from odoo.addons.mail.tools.web_push import push_to_end_point, DeviceUnreachableError

_logger = logging.getLogger(__name__)


class HrMaestroPushDevice(models.Model):
    _name = 'hr.maestro.push.device'
    _description = 'Dispositivo de push do app Maestro (PWA)'

    employee_id = fields.Many2one('hr.employee', string='Funcionário', required=True,
                                   index=True, ondelete='cascade')
    endpoint = fields.Char(string='Endpoint do navegador', required=True)
    keys = fields.Char(string='Chaves do navegador', required=True)

    _sql_constraints = [
        ('endpoint_uniq', 'unique(endpoint)', 'Este dispositivo já está registrado.'),
    ]

    @api.model
    def _register(self, employee, endpoint, keys):
        device = self.sudo().search([('endpoint', '=', endpoint)], limit=1)
        values = {'employee_id': employee.id, 'keys': json.dumps(keys)}
        if device:
            device.write(values)
        else:
            values['endpoint'] = endpoint
            self.sudo().create(values)

    def _send(self, title, body, url=None):
        ir_params = self.env['ir.config_parameter'].sudo()
        vapid_private_key = ir_params.get_param('mail.web_push_vapid_private_key')
        vapid_public_key = self.env['mail.push.device'].sudo().get_web_push_vapid_public_key()
        if not vapid_private_key:
            return
        base_url = ir_params.get_param('web.base.url')
        payload = json.dumps({'title': title, 'body': body, 'url': url or '/maestro/app'})
        session = Session()
        devices_to_unlink = self.browse()
        for device in self.sudo():
            try:
                push_to_end_point(
                    base_url=base_url,
                    device={'id': device.id, 'endpoint': device.endpoint, 'keys': device.keys},
                    payload=payload,
                    vapid_private_key=vapid_private_key,
                    vapid_public_key=vapid_public_key,
                    session=session,
                )
            except DeviceUnreachableError:
                devices_to_unlink |= device
            except Exception:
                _logger.exception('Maestro push: falha ao enviar notificação (device %s)', device.id)
        if devices_to_unlink:
            devices_to_unlink.unlink()

    @api.model
    def _notify_employee(self, employee, title, body, url=None):
        devices = self.sudo().search([('employee_id', '=', employee.id)])
        if devices:
            devices._send(title, body, url)
