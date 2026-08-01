# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import randint

from odoo import fields, models


class FetchmailTag(models.Model):
    _name = 'fetchmail.tag'
    _description = 'Inbox Tag'
    _order = 'name'

    name = fields.Char(required=True)
    color = fields.Integer(default=lambda self: randint(1, 11))

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Tag name already exists.'),
    ]

    def search_or_create(self, name):
        """Return tag with given name (case-insensitive), creating it if not found."""
        tag = self.search([('name', '=ilike', name)], limit=1)
        return tag or self.create({'name': name})
