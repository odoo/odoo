
from itertools import accumulate

from odoo import api, fields, models
from odoo.tools import Query


class AccountRoot(models.Model):
    _name = 'account.root'
    _description = 'Account codes first 2 digits'
    _auto = False
    _table_query = '0'

    name = fields.Char(compute='_compute_root')
    parent_id = fields.Many2one('account.root', compute='_compute_root')

    def browse(self, ids=()):
        if isinstance(ids, str):
            ids = (ids,)
        return super().browse(ids)

    def _search(self, domain, offset=0, limit=None, order=None) -> Query:
        match domain:
            case [('id', 'in', ids)]:
                return self.browse(sorted(ids))._as_query()
            case [('id', 'parent_of', ids)]:
                return self.browse(sorted({s for _id in ids for s in accumulate(_id)}))._as_query()
        raise NotImplementedError

    @api.model
    def _from_account_code(self, code):
        return self.browse(code and code[:2])

    def _compute_root(self):
        for root in self:
            root.name = root.id
            root.parent_id = self.browse(root.id[:-1] if len(root.id) > 1 else False)
