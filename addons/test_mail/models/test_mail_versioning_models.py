from odoo import models, fields

class Foo(models.Model):
    _name = "foo.model"
    _description = "Foo Model"
    _inherit = ["mail.versioning.mixin"]

    name = fields.Char()

class Bar(models.Model):
    _name = "bar.model"
    _description = "Bar Model"
    _inherit = ["mail.versioning.mixin"]

    name = fields.Char()
    foo_id = fields.Many2one("foo.model")
