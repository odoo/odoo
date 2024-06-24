# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    test_bool = fields.Boolean(default=True, config_parameter='test_new_api.test_bool')
    test_int = fields.Integer(default=30, config_parameter='test_new_api.test_int')
    test_float = fields.Float(digits=(10, 7), default=1.5, config_parameter='test_new_api.test_float')
