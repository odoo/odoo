from odoo import fields, models


class LibraryMember(models.Model):
    _name = 'library.member'
    _description = 'Library Member'
    _order = 'name'

    name = fields.Char(required=True)
    email = fields.Char()
    phone = fields.Char()
