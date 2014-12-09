from openerp import models, fields, api


class crm_configuration(models.TransientModel):
    _name = 'sale.config.settings'
    _inherit = 'sale.config.settings'

    wsServer = fields.Char("WebSocket", help="The URL of your WebSocket")
    pbx_ip = fields.Char("PBX Server IP", help="The IP adress of your PBX Server")

    @api.multi
    def set_pbx_ip(self):
        self.env['ir.config_parameter'].set_param('crm.voip.pbx_ip', self[0].pbx_ip)

    @api.multi
    def set_wsServer(self):
        self.env['ir.config_parameter'].set_param('crm.voip.wsServer', self[0].wsServer)

    @api.multi
    def get_default_pbx_ip(self):
        params = self.env['ir.config_parameter']

        pbx_ip = params.get_param('crm.voip.pbx_ip', default='localhost')
        return {'pbx_ip': pbx_ip}

    @api.multi
    def get_default_wsServer(self):
        params = self.env['ir.config_parameter']

        wsServer = params.get_param('crm.voip.wsServer', default='ws://localhost')
        return {'wsServer': wsServer}
