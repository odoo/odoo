# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.osv import expression


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        user_query = super()._name_search(name, domain, operator, limit, order)
        if limit is None:
            return user_query
        user_ids = list(user_query)
        if self._uid in user_ids:
            if user_ids.index(self._uid) != 0:
                user_ids.remove(self._uid)
                user_ids.insert(0, self._uid)
        elif limit and len(user_ids) == limit:
            new_user_ids = super()._name_search(
                name,
                expression.AND([domain or [], [('id', '=', self._uid)]]),
                operator,
                limit=1,
            )
            if new_user_ids:
                user_ids.pop()
                user_ids.insert(0, self._uid)
        return user_ids
