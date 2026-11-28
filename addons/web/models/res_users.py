# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.fields import Domain
from odoo.http import request

SKIP_CAPTCHA_LOGIN = object()


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def name_search(self, name='', domain=None, operator='ilike', limit=100):
        # if we have a search with a limit, move current user as the first result
        domain = Domain(domain or Domain.TRUE)
        user_list = super().name_search(name, domain, operator, limit)
        uid = self.env.uid
        # index 0 is correct not Falsy in this case, use None to avoid ignoring it
        if (index := next((i for i, (user_id, _name) in enumerate(user_list) if user_id == uid), None)) is not None:
            # move found user first
            user_tuple = user_list.pop(index)
            user_list.insert(0, user_tuple)
        elif limit is not None and len(user_list) == limit:
            # user not found and limit reached, try to find the user again
            if user_tuple := super().name_search(name, domain & Domain('id', '=', uid), operator, limit=1):
                user_list = [user_tuple[0], *user_list[:-1]]
        return user_list

    @api.model
    @api.readonly
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        domain = Domain(domain)
        uid = self.env.uid
        if (
            not self.env.context.get('current_user_first')
            or limit == 1
            or not self.search_count(domain & Domain('id', '=', uid), limit=1)
        ):
            return super().web_search_read(domain, specification, offset, limit, order, count_limit)
        others_domain = domain & Domain('id', '!=', uid)
        if offset:
            result = super().web_search_read(others_domain, specification, offset - 1, limit, order, count_limit)
        else:
            result = super().web_search_read(others_domain, specification, 0, limit and limit - 1, order, count_limit)
            result['records'] = self.browse(uid).web_read(specification) + result['records']
        result['length'] += 1
        return result

    def _on_webclient_bootstrap(self):
        self.ensure_one()

    def _should_captcha_login(self, credential):
        if request and request.env.context.get('skip_captcha_login') is SKIP_CAPTCHA_LOGIN:
            return False
        return credential['type'] == 'password'
