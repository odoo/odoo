from odoo import fields, models


class ResConfigTest(models.Model):
    _name = 'res.config.test'
    _inherit = ['res.config.settings']
    _description = 'res.config test'

    parameter_with_default = fields.Integer(
        string='Test parameter 1',
        config_parameter='resConfigTest.parameter_with_default',
        default=1000,
    )

    # TODO (rugo) Not sure why this is here (?)
    param2 = fields.Many2one('res.config', config_parameter="resConfigTest.parameter2")
