# -*- coding: utf-8 -*-

from odoo import models, fields, api

class binary_test(models.Model):
    _name = 'binary_test.binary_test'

    name = fields.Char()
    value = fields.Binary()

    @api.onchange('value')
    def onchange_value(self):
        print (self.value or '')[:10]
        import pdb;pdb.set_trace()
