# -*- coding: utf-8 -*-
from openerp import api, models, fields

class change_defaults(models.Model):
    _inherit = 'test_new_api.defaults'

    description = fields.Char(required=True, compute="description_default")

    @api.record
    def description_default(self):
        self.description = u"This is a thing"
