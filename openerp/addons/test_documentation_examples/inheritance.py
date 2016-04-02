# -*- coding: utf-8 -*-

from openerp import models, fields

class Inheritance0(models.Model):
    _name = 'inheritance.0'

    name = fields.Char()

    def call(self):
        return self.check("model 0")

    def check(self, s):
        return "This is {} record {}".format(s, self.name)

class Inheritance1(models.Model):
    _name = 'inheritance.1'
    _inherit = 'inheritance.0'

    def call(self):
        return self.check("model 1")
