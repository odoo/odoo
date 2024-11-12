# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.osv import expression


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        # if we have a search with a limit, move current user as the first result
        user_list = super().name_search(name, args, operator, limit)
        uid = self._uid
        if index := next((i for i, (user_id, _name) in enumerate(user_list) if user_id == uid), False):
            # move found user first
            user_tuple = user_list.pop(index)
            user_list.insert(0, user_tuple)
        elif limit is not None and len(user_list) == limit:
            # user not found and limit reached, try to find the user again
            if user_tuple := super().name_search(name, expression.AND([args or [], [('id', '=', uid)]]), operator, limit=1):
                user_list = [user_tuple[0], *user_list[:-1]]
        return user_list

    def _on_webclient_bootstrap(self):
        self.ensure_one()
