# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Test_New_ApiMove_Line(models.Model):
    _name = 'test_new_api.move'
    _inherit = ['test_new_api.move', 'test_inherit.mixin']
