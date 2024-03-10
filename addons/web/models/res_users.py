# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools.sql import SQL

class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=None):
        args = args or [] + self._search_display_name(name, operator)
        query = self._search(args, limit=limit, order=self._order)
        query.order = SQL(",").join(
            SQL("%s = %s",self._field_to_sql(self.table, fname="id"), self._uid),
            query.order)
        return [(record.id, record.display_name) for record in query.sudo()]
