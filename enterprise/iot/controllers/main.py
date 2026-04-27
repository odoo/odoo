# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import itertools
import json
import logging
import pathlib
import pprint
import re
import textwrap
import werkzeug
import zipfile

from odoo import http
from odoo.http import request, Response
from odoo.modules import get_module_path
from odoo.tools.misc import str2bool

_logger = logging.getLogger(__name__)

_iot_logger = logging.getLogger(__name__ + '.iot_log')
# We want to catch any log level that the IoT send
_iot_logger.setLevel(logging.DEBUG)

_logger = logging.getLogger(__name__)

class IoTController(http.Controller):
    def _search_box(self, mac_address):
        return request.env['iot.box'].sudo().search([('identifier', '=', mac_address)], limit=1)

    @http.route('/iot/get_handlers', type='http', auth='public', csrf=False)
    def download_iot_handlers(self, auto, **kwargs):
        mac = kwargs.get('mac')
        identifier = kwargs.get('identifier')

        # Check mac is of one of the IoT Boxes
        box = self._search_box(mac) if mac else self._search_box(identifier)
        if not box or (auto == 'True' and not box.drivers_auto_update):
            raise werkzeug.exceptions.Unauthorized(
                description="No IoT box found with mac/identifier '%s' or auto update disabled on the box." % mac
            )

        module_ids = request.env['ir.module.module'].sudo().search([('state', '=', 'installed')])
        modules = module_ids.mapped('name') + ["hw_drivers"]

        if re.search(r"\d{4}\.\d{2}\.\d{2}", box.version):
            # New IoT Boxes get drivers from git repository, not from installed modules
            # for partners/clients that want to download custom drivers from the db, we only download
            # custom drivers, to avoid overwriting the git ones
            modules = [
                m for m in modules
                if m not in {"iot", "hw_drivers", "pos_blackbox_be", "pos_l10n_se", "pos_iot_six", "quality_iot"}
            ]

        fobj = io.BytesIO()
        with zipfile.ZipFile(fobj, 'w', zipfile.ZIP_DEFLATED) as zf:
            for module in modules:
                module_path = get_module_path(module)
                if module_path:
                    iot_handlers = pathlib.Path(module_path) / 'iot_handlers'
                    for handler in iot_handlers.glob('*/*'):
                        if handler.is_file() and not handler.name.startswith(('.', '_')):
                            # In order to remove the absolute path
                            zf.write(handler, handler.relative_to(iot_handlers))

        return request.make_response(fobj.getvalue(), headers=[('Content-Type', 'application/zip')])

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

    @http.route(['/iot/printer/status', '/iot/box/send_websocket'], type='json', auth='public')
    def listen_iot_printer_status(self, **kwargs):
        """
        Called by the IoT once the printing operation is over. We then forward
        the acknowledgment to the user who made the print request to inform him
        of the success of the operation.
        """
        print_id = kwargs.get('print_id') or kwargs.get('session_id')  # compatibility w/ newer IoT boxes
        iot_mac = kwargs.get('iot_mac') or kwargs.get("iot_box_identifier")  # compatibility w/ newer IoT boxes
        device_identifier = kwargs.get('device_identifier')

        if not print_id or not iot_mac or not device_identifier:
            # in V17.0 we don't handle websocket callbacks for all actions,
            # this is meant to avoid traceback when using an IoT Box in V18.4+
            return

        if isinstance(device_identifier, str) and isinstance(print_id, str):
            box = self._search_box(iot_mac)
            if not box:
                _logger.warning("No IoT found with mac/identifier '%s'. Request ignored", iot_mac)
                return
            iot_device = request.env["iot.device"].sudo().search([
                    ('identifier', '=', device_identifier),
                    ('iot_id', '=', box.id)
                ],
                limit=1
            )

            if not iot_device:
                _logger.warning("No IoT device found with identifier '%s' (iot_mac: %s). Request ignored", device_identifier, iot_mac)
                return

            iot_channel = request.env['iot.channel'].sudo().get_iot_channel()
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
        iot_identifier = iot_box['identifier']  # IoT Mac Address
        iot_serial_number = iot_box.get('serial_number')
        new_iot_name = iot_box['name']
        new_iot_ip = iot_box['ip']
        new_iot_version = iot_box['version']
        box = request.env['iot.box'].sudo().search([('identifier', 'in', [iot_identifier, iot_serial_number])], limit=1)
        create_update_value = {
            'name': new_iot_name,
            'ip': new_iot_ip,
            'version': new_iot_version,
        }
        if box:
            if box.identifier != iot_identifier and box.identifier == iot_serial_number:
                create_update_value['identifier'] = iot_identifier
            if (box.name, box.ip, box.version, box.identifier) != (new_iot_name, new_iot_ip, new_iot_version, create_update_value.get('identifier')):
                _logger.info('Updating IoT %s with data: %s', box, create_update_value)
                box.write(create_update_value)
        else:
            iot_token = request.env['ir.config_parameter'].sudo().get_param('iot_token', '').strip('\n')
            if iot_token and iot_token == iot_box['token']:
                create_update_value['identifier'] = iot_identifier
                _logger.info('Creating IoT with data: %s', create_update_value)
                box = request.env['iot.box'].sudo().create(create_update_value)
            else:
                _logger.warning('Token mismatch for IoT %s expected %s got %s', iot_identifier, iot_token, iot_box['token'])
                return

        _logger.info('IoT %s devices:\n%s', box, pprint.pformat(devices))
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
                    # Special case to handle serial port change for blackbox
                    if data_device['type'] == 'fiscal_data_module' and 'BODO001' in data_device['name']:
                        existing_blackbox = connected_iot_devices.search([
                            ('iot_id', '=', box.id), ('name', 'like', 'BODO001'), ('type', '=', 'fiscal_data_module')
                        ], limit=1)
                        if existing_blackbox:
                            existing_blackbox.write({'identifier': device_identifier})
                            connected_iot_devices |= existing_blackbox
                            continue

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
                            'subtype': data_device.get('subtype', ''),
                        })
                    elif device and device.type != data_device.get('type') or (device.subtype == '' and device.type == 'printer'):
                        device.write({
                        'name': data_device.get('name'),
                        'type': data_device.get('type'),
                        'manufacturer': data_device.get('manufacturer'),
                        'subtype': data_device.get('subtype', '')
                        })

                    connected_iot_devices |= device
            # Mark the received devices as connected, disconnect the others.
            connected_iot_devices.write({'connected': True})
            (previously_connected_iot_devices - connected_iot_devices).write({'connected': False})
            return request.env['iot.channel'].sudo().get_iot_channel()

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
