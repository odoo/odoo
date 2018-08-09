import base64

from odoo import api, fields, models, exceptions

# ----------------------------------------------------------
# Models for client
# ----------------------------------------------------------
class IotBox(models.Model):
    _name = 'iot.box'

    name = fields.Char('Name', readonly=True)
    identifier = fields.Char(string='Identifier (Mac Address)', readonly=True)
    device_ids = fields.One2many('iot.device', 'iot_id', string="Devices", readonly=True)
    ip = fields.Char('IP Address', readonly=True)
    screen_url = fields.Char('Screen URL', help="Url of the page that will be displayed by hdmi port of the box.")


class IotDevice(models.Model):
    _name = 'iot.device'

    iot_id = fields.Many2one('iot.box', string='IoT Box', required = True)
    name = fields.Char('Name')
    identifier = fields.Char(string='Identifier', readonly=True)
    type = fields.Selection([
        ('printer', 'Printer'),
        ('camera', 'Camera'),
        ('device', 'Device'),
        ], readonly=True, default='device', string='Type',
        help="Type of device.")
    connection = fields.Selection([
        ('network', 'Network'),
        ('direct', 'USB'),
        ('bluetooth', 'Bluetooth')
        ], readonly=True, string="Connection",
        help="Type of connection.")
    report_ids = fields.One2many('ir.actions.report', 'device_id', string='Reports')

    def name_get(self):
        return [(i.id, "[" + i.iot_id.name +"] " + i.name) for i in self]


class IrActionReport(models.Model):
    _inherit = 'ir.actions.report'

    device_id = fields.Many2one('iot.device', string='IoT Device', domain="[('device_type', '=', 'printer')]",
                                help='When setting a device here, the report will be printed through this device on the iotbox')

    def iot_render(self, res_ids, data=None):
        if self.mapped('device_id'):
            device = self.mapped('device_id')[0]
        else:
            device = self.env['iot.device'].browse(data['device_id'])
        composite_url = "http://" + device.iot_id.ip + ":8069/driveraction/" + device.identifier
        datas = self.render(res_ids, data=data)
        type = datas[1]
        data_bytes = datas[0]
        data_base64 = base64.b64encode(data_bytes)
        return composite_url, type, data_base64