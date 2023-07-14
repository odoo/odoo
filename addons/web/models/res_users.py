# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.osv import expression


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        user_ids = list(super()._name_search(name, domain, operator, limit, order))
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

    @api.model
    def web_search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, count_limit=None):
        result = super().web_search_read(
            expression.AND([domain or [], [('id', '!=', self._uid)]]),
            fields, offset, limit, order, count_limit)

        length = result['length']
        records = list(result['records'])

        if offset == 0:
            current_user = super().search_read(
                domain=expression.AND([domain or [], [('id', '=', self._uid)]]),
                fields=fields,
                limit=1)
            if current_user:
                records.insert(0, current_user[0])
                if length < count_limit:
                    length += 1
                if len(records) == limit + 1:
                    records.pop()
        else:
            if length < count_limit and self.search(
                    domain=expression.AND([domain or [], [('id', '=', self._uid)]]),
                    limit=1
            ):
                length += 1

        return {
            'records': records,
            'length': length
        }
