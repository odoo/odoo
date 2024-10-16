# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.addons import test_inherits


# We add a field on this model
class TestUnit(test_inherits.TestUnit):

    second_name = fields.Char()
