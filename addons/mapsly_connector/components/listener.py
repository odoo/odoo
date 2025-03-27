from datetime import datetime
import requests
import logging
import json

from odoo.addons.component_event import skip_if
from odoo.addons.component.core import Component
from odoo.models import BaseModel


class MapslyEventListener(Component):
    CONST_HOOK_URL = 'https://adapter.mapsly.com'

    CONST_EVENT_CREATE = 'create'
    CONST_EVENT_UPDATE = 'update'
    CONST_EVENT_DELETE = 'delete'

    _name = 'mapsly.event.listener'
    _inherit = 'base.event.listener'
    _logger = logging.getLogger(__name__)

    @skip_if(lambda self, record, fields: record._name == 'bus.presence' or record._name == 'bus.bus')
    def on_record_create(self, record, fields=None):
        api_key = self.get_api_key()
        if not api_key:
            return

        url = self.get_hook_url(self.CONST_EVENT_CREATE)
        data = json.dumps({'id': record.id, 'entity': record._name, 'values': self.get_values(record, fields)})
        headers = {'x-api-key': api_key, 'referer': self.get_odoo_url(), 'Content-Type': 'application/json'}

        self._logger.log(logging.INFO, 'on_record_create %s send webhook to %s with data %s and headers %s', record._name, url, data, headers)

        requests.post(url, data=data, headers=headers, verify=False)

    @skip_if(lambda self, record, fields: record._name == 'bus.presence' or record._name == 'bus.bus')
    def on_record_write(self, record, fields=None):
        api_key = self.get_api_key()
        if not api_key:
            return

        url = self.get_hook_url(self.CONST_EVENT_UPDATE)
        data = json.dumps({'id': record.id, 'entity': record._name, 'values': self.get_values(record, fields)})
        headers = {'x-api-key': api_key, 'referer': self.get_odoo_url(), 'Content-Type': 'application/json'}

        self._logger.log(logging.INFO, 'on_record_write %s send webhook to %s with data %s and headers %s', record._name, url, data, headers)

        requests.post(url, data=data, headers=headers, verify=False)


    @skip_if(lambda self, record: record._name == 'bus.presence' or record._name == 'bus.bus')
    def on_record_unlink(self, record):
        api_key = self.get_api_key()
        if not api_key:
            return

        url = self.get_hook_url(self.CONST_EVENT_DELETE)
        data = json.dumps({'id': record.id, 'entity': record._name})
        headers = {'x-api-key': api_key, 'referer': self.get_odoo_url(), 'Content-Type': 'application/json'}

        self._logger.log(logging.INFO, 'on_record_unlink %s send webhook to %s with data %s and headers %s', record._name, url, data, headers)

        requests.post(url, data=data, headers=headers, verify=False)

    def get_hook_url(self, event):
        subdomain = 'adapter'
        mapsly_adapter_server = self.env['ir.config_parameter'].get_param('mapsly.mapsly_adapter_server')
        if (mapsly_adapter_server):
            subdomain = subdomain + '-' + mapsly_adapter_server
        return 'https://' + subdomain + '.mapsly.com' + '/odoo/webhook/' + event

    def get_api_key(self):
        config_parameter = self.env['ir.config_parameter'].get_param('mapsly.api_key')
        if not config_parameter:
            return None
        return config_parameter

    def get_odoo_url(self):
        config_parameter = self.env['ir.config_parameter'].get_param('web.base.url')
        if not config_parameter:
            return None
        return config_parameter

    def get_values(self, record, fields):
        values = {}
        for field in fields:
            value = getattr(record, field)
            try:
                json.dumps(value)
                values[field] = value
            except (TypeError, OverflowError):
                if isinstance(value, BaseModel):
                    values[field] = value.id
                else:
                    if isinstance(value, datetime):
                        values[field] = value.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        values[field] = str(value)
        return values
