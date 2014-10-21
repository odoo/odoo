from openerp import models, fields, api


class crm_configuration(models.TransientModel):
    _name = 'sale.config.settings'
    _inherit = 'sale.config.settings'

    asterisk_url = fields.Char("Asterisk Server")
    asterisk_login = fields.Char("Asterisk Login")
    asterisk_password = fields.Char("Asterisk Password")
    asterisk_phone = fields.Char("Salesman's Phone", size=64)

    @api.one
    def set_default_asterisk_url(self):
        self.env['ir.values'].set_default('sale.config.settings', 'asterisk_url', self.asterisk_url)

    @api.one
    def set_default_asterisk_login(self):
        self.env['ir.values'].set_default('sale.config.settings', 'asterisk_login', self.asterisk_login)

    @api.one
    def set_default_asterisk_password(self):
        self.env['ir.values'].set_default('sale.config.settings', 'asterisk_password', self.asterisk_password)

    @api.one
    def set_default_asterisk_phone(self):
        self.env['ir.values'].set_default('sale.config.settings', 'asterisk_phone', self.asterisk_phone)