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
        # index 0 is correct not Falsy in this case, use None to avoid ignoring it
        if (index := next((i for i, (user_id, _name) in enumerate(user_list) if user_id == uid), None)) is not None:
            # move found user first
            user_tuple = user_list.pop(index)
            user_list.insert(0, user_tuple)
        elif limit is not None and len(user_list) == limit:
            # user not found and limit reached, try to find the user again
            if user_tuple := super().name_search(name, expression.AND([args or [], [('id', '=', uid)]]), operator, limit=1):
                user_list = [user_tuple[0], *user_list[:-1]]
        return user_list

    @api.model
    @api.readonly
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        # if we have a search with a limit, move current user as the first result
        user_list = super().web_search_read(domain, specification, offset, limit, order, count_limit)
        uid = self._uid
        if index := next((i for (i, rec) in enumerate(user_list['records']) if rec['id'] == uid), False):
            # move found user first
            user_record = user_list['records'].pop(index)
            user_list['records'].insert(0, user_record)
        elif limit is not None and user_list.length == limit:
            # user not found and limit reached, try to find the user again
            if user_record := super().web_search_read(expression.AND([domain or [], [('id', '=', uid)]]), specification, offset, limit=1, order=order, count_limit=count_limit):
                user_list['records'] = [user_record['records'][0], *user_list['records'][:-1]]
        return user_list

    def _on_webclient_bootstrap(self):
        self.ensure_one()
