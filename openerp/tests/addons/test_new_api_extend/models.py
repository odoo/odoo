# -*- coding: utf-8 -*-
from openerp import Model, fields
from openerp import one

class change_defaults(Model):
    _inherit = 'test_new_api.defaults'

    description = fields.Char(required=True, compute="description_default")

    @one
    def description_default(self):
        self.description = u"This is a thing"
