# -*- coding: utf-8 -*-

from odoo.osv import expression
from odoo import models, fields, api

class account_account_tag(models.Model):
    _inherit = 'account.account.tag'

    # since Odoo 9, the parent view accounts (111, 112, etc) ware removed which's caused some difficulties for VAS compliance legal reports
    # the code field is added in account.account.tag to group accounts and sub accounts by tags which look like parent accounts were.
    code = fields.Char(string="Code", size=20, help="The unique code of the tag. For example, 111 for cash, 112 for cash in banks, etc.")

    @api.multi
    def name_get(self):
        """
        name_get that supports displaying tags with their code as prefix
        """
        result = []
        for tag in self:
            if tag.code:
                result.append((tag.id, '%s - %s' % (tag.code, tag.name)))
            else:
                result.append((tag.id, tag.name))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        """
        name search that supports searching tags by tag code
        """
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', '=ilike', name + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&'] + domain
        tags = self.search(domain + args, limit=limit)
        return tags.name_get()
