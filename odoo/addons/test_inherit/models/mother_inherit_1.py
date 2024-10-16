# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.addons import test_inherit


# We add a new field in the parent model. Because of a recent refactoring, this


# feature was broken. These models rely on that feature.
class TestInheritMother(models.Model, test_inherit.TestInheritMother):

    field_in_mother = fields.Char()
    partner_id = fields.Many2one('res.partner')
    state = fields.Selection([('a', 'A'), ('b', 'B')], default='a')

    # extend the name field: make it required and change its default value
    name = fields.Char(required=True, default='Bar')

    def bar(self):
        return 42


class Test_Mother_Underscore(models.Model, test_inherit.TestInheritMother):
    _description = 'Test Inherit Underscore'


# pylint: disable=E0102
class Test_Mother_Underscore(models.Model, test_inherit.Test_Mother_Underscore):  # noqa: F811

    foo = fields.Char()
