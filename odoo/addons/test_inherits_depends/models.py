# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import test_inherits

from odoo import models, fields


# We add a field on this model
class TestUnit(models.Model, test_inherits.TestUnit):

    second_name = fields.Char()
