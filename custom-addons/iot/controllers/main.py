# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import itertools
import json
import logging
import pathlib
import textwrap
import zipfile

from odoo import http
from odoo.http import request, Response
from odoo.modules import get_module_path
from odoo.tools.misc import str2bool

_iot_logger = logging.getLogger(__name__ + '.iot_log')
# We want to catch any log level that the IoT send
_iot_logger.setLevel(logging.DEBUG)

_logger = logging.getLogger(__name__)

class IoTController(http.Controller):
    def _search_box(self, mac_address):
        return request.env['iot.box'].sudo().search([('identifier', '=', mac_address)], limit=1)

    @http.route('/iot/get_handlers', type='http', auth='public', csrf=False)
    def download_iot_handlers(self, mac, auto):
        # Check mac is of one of the IoT Boxes
        box = self._search_box(mac)
        if not box or (auto == 'True' and not box.drivers_auto_update):
            return ''

        module_ids = request.env['ir.module.module'].sudo().search([('state', '=', 'installed')])
        fobj = io.BytesIO()
        with zipfile.ZipFile(fobj, 'w', zipfile.ZIP_DEFLATED) as zf:
            for module in module_ids.mapped('name') + ['hw_drivers']:
                module_path = get_module_path(module)
                if module_path:
                    iot_handlers = pathlib.Path(module_path) / 'iot_handlers'
                    for handler in iot_handlers.glob('*/*'):
                        if handler.is_file() and not handler.name.startswith(('.', '_')):
                            # In order to remove the absolute path
                            zf.write(handler, handler.relative_to(iot_handlers))

        return fobj.getvalue()

    @http.route('/iot/keyboard_layouts', type='http', auth='public', csrf=False)
    def load_keyboard_layouts(self, available_layouts):
        if not request.env['iot.keyboard.layout'].sudo().search_count([]):
            request.env['iot.keyboard.layout'].sudo().create(json.loads(available_layouts))
        return ''

    @http.route('/iot/box/<string:identifier>/display_url', type='http', auth='public')
    def get_url(self, identifier):
        urls = {}
        iotbox = self._search_box(identifier)
        if iotbox:
            iot_devices = iotbox.device_ids.filtered(lambda device: device.type == 'display')
            for device in iot_devices:
                urls[device.identifier] = device.display_url
        return json.dumps(urls)

    @http.route('/iot/printer/status', type='json', auth='public')
    def listen_iot_printer_status(self, print_id, device_identifier, iot_mac=None):
        """
        Called by the IoT once the printing operation is over. We then forward
        the acknowledgment to the user who made the print request to inform him
        of the sucess of the operation.
        """
        if isinstance(device_identifier, str) and isinstance(print_id, str):
            iot_device_domain = [('identifier', '=', device_identifier)]
            if iot_mac:  # Might not exists on older version of 17 of IoT boxes
                box = self._search_box(iot_mac)
                if not box:
                    _logger.warning("No IoT found with mac/identifier '%s'. Request ignored", iot_mac)
                    return
                iot_device_domain.append(('iot_id', '=', box.id))
            # Note: in the case on which iot_mac is not given, we might
            # accidentally find a device with the same identifier from another IoT
            iot_device = request.env["iot.device"].sudo().search(iot_device_domain, limit=1)

            if not iot_device:
                _logger.warning("No IoT device found with identifier '%s' (iot_mac: %s). Request ignored", device_identifier, iot_mac)
                return

            iot_channel = request.env['iot.channel'].sudo().with_company(iot_device.company_id).get_iot_channel()
            request.env['bus.bus']._sendone(iot_channel, 'print_confirmation', {
                'print_id': print_id,
                'device_identifier': device_identifier
            })

    @http.route('/iot/setup', type='json', auth='public')
    def update_box(self, **kwargs):
        """
        This function receives a dict from the iot box with information from it 
        as well as devices connected and supported by this box.
        This function create the box and the devices and set the status (connected / disconnected)
         of devices linked with this box
        """
        if kwargs:
            # Box > V19
            iot_box = kwargs['iot_box']
            devices = kwargs['devices']
        else:
            # Box < V19
            data = request.jsonrequest
            iot_box = data
            devices = data['devices']

         # Update or create box
        box = self._search_box(iot_box['identifier'])
        if box:
            box = box[0]
            box.ip = iot_box['ip']
            box.name = iot_box['name']
        else:
            iot_token = request.env['ir.config_parameter'].sudo().search([('key', '=', 'iot_token')], limit=1)
            if iot_token.value.strip('\n') == iot_box['token']:
                box = request.env['iot.box'].sudo().create({
                    'name': iot_box['name'],
                    'identifier': iot_box['identifier'],
                    'ip': iot_box['ip'],
                    'version': iot_box['version'],
                })

        # Update or create devices
        if box:
            previously_connected_iot_devices = request.env['iot.device'].sudo().search([
                ('iot_id', '=', box.id),
                ('connected', '=', True)
            ])
            connected_iot_devices = request.env['iot.device'].sudo()
            for device_identifier in devices:
                available_types = [s[0] for s in request.env['iot.device']._fields['type'].selection]
                available_connections = [s[0] for s in request.env['iot.device']._fields['connection'].selection]

                data_device = devices[device_identifier]
                if data_device['type'] in available_types and data_device['connection'] in available_connections:
                    if data_device['connection'] == 'network':
                        device = request.env['iot.device'].sudo().search([('identifier', '=', device_identifier)])
                    else:
                        device = request.env['iot.device'].sudo().search([('iot_id', '=', box.id), ('identifier', '=', device_identifier)])
                
                    # If an `iot.device` record isn't found for this `device`, create a new one.
                    if not device:
                        device = request.env['iot.device'].sudo().create({
                            'iot_id': box.id,
                            'name': data_device['name'],
                            'identifier': device_identifier,
                            'type': data_device['type'],
                            'manufacturer': data_device['manufacturer'],
                            'connection': data_device['connection'],
                        })
                    elif device and device.type != data_device.get('type'):
                        device.write({
                        'name': data_device.get('name'),
                        'type': data_device.get('type'),
                        'manufacturer': data_device.get('manufacturer')
                        })

                    connected_iot_devices |= device
            # Mark the received devices as connected, disconnect the others.
            connected_iot_devices.write({'connected': True})
            (previously_connected_iot_devices - connected_iot_devices).write({'connected': False})
            iot_channel = request.env['iot.channel'].sudo().with_company(box.company_id).get_iot_channel()
            return iot_channel

    def _is_iot_log_enabled(self):
        return str2bool(request.env['ir.config_parameter'].sudo().get_param('iot.should_log_iot_logs', True))

    @http.route('/iot/log', type='http', auth='public', csrf=False)
    def receive_iot_log(self):
        IOT_ELEMENT_SEPARATOR = b'<log/>\n'
        IOT_LOG_LINE_SEPARATOR = b','
        IOT_MAC_PREFIX = b'mac '

        def log_line_transformation(log_line):
            split = log_line.split(IOT_LOG_LINE_SEPARATOR, 1)
            return {'levelno': int(split[0]), 'line_formatted': split[1].decode('utf-8')}

        def log_current_level():
            _iot_logger.log(
                log_level,
                "%s%s",
                init_log_message,
                textwrap.indent("\n".join(['', *log_lines]), ' | ')
            )

        def finish_request():
            return Response(status=200)

        if not self._is_iot_log_enabled():
            return finish_request()

        request_data = request.httprequest.get_data()
        if request_data.endswith(IOT_ELEMENT_SEPARATOR):
            # Do not use rstrip as some characters of the separator might be at the end of the log line
            request_data = request_data[:-len(IOT_ELEMENT_SEPARATOR)]
        request_data_split = request_data.split(IOT_ELEMENT_SEPARATOR)
        if len(request_data_split) < 2:
            return finish_request()

        mac_details = request_data_split.pop(0)
        if not mac_details.startswith(IOT_MAC_PREFIX):
            return finish_request()

        mac_address = mac_details[len(IOT_MAC_PREFIX):]
        iot_box = self._search_box(mac_address)
        if not iot_box:
            return finish_request()

        log_details = map(log_line_transformation, request_data_split)
        init_log_message = "IoT box log '%s' #%d received:" % (iot_box.name, iot_box.id)

        for log_level, log_group in itertools.groupby(log_details, key=lambda log: log['levelno']):
            log_lines = [log_line['line_formatted'] for log_line in log_group]
            log_current_level()

        return finish_request()
