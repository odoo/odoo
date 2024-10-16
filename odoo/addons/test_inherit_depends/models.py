# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.addons import test_new_api, test_inherit


class Test_New_ApiFoo(test_new_api.Test_New_ApiFoo, test_inherit.Test_Inherit_Mixin):


class TestInheritMother(test_inherit.TestInheritMother):

    # extend again the selection of the state field: 'e' must precede 'e'
    state = fields.Selection(selection_add=[('g', 'G')])
    field_in_mother_5 = fields.Char()

    def foo(self):
        return super().foo() * 2
