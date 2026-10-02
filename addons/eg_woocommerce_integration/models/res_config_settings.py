from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    tax_rate = fields.Selection([('odoo_tax', 'Default Odoo Tax'), ('woocommerce_tax', 'Woccommerce Tax')])
    create_tax_rate = fields.Boolean(string='Create New Tax Rate')

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        icpSudo = self.env['ir.config_parameter'].sudo()  # it is given all access
        res.update(
            tax_rate=icpSudo.get_param('eg_new_woocommerce_integration.tax_rate', default='woocommerce_tax'),
            create_tax_rate=icpSudo.get_param('eg_new_woocommerce_integration.create_tax_rate', default=True), )
        return res

    @api.model
    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        icpSudo = self.env['ir.config_parameter'].sudo()
        icpSudo.set_param("eg_new_woocommerce_integration.tax_rate", self.tax_rate)
        return res

    def _onchange_tax_rate(self):
        if self.tax_rate == 'odoo_tax':
            self.create_tax_rate = False
