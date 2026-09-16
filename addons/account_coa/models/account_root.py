from itertools import accumulate

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import Query


class AccountRoot(models.Model):
    """Virtual model for the first two characters of an account code."""

    _name = "account.root"
    _description = "Account codes first 2 digits"
    _auto = False
    _table_query = "0"
    _search_visibility_fields = ()

    name = fields.Char(compute="_compute_root")
    parent_id = fields.Many2one(
        comodel_name="account.root",
        compute="_compute_root",
    )

    @api.private
    def browse(self, ids=()):
        if isinstance(ids, str):
            ids = (ids,)
        return super().browse(ids)

    def _search(self, domain, offset=0, limit=None, order=None, **kw) -> Query:
        match list(domain):
            case [("id", "in", ids)]:
                return self.browse(sorted(ids))._as_query()
            case [("id", "parent_of", ids)]:
                return self.browse(
                    sorted({s for _id in ids for s in accumulate(_id)})
                )._as_query()
        raise UserError(self.env._("Filter on the Account or its Display Name instead"))

    @api.model
    def _from_account_code(self, code):
        """Return the account.root record for an account code's first two characters."""
        return self.browse(code and code[:2])

    def _compute_root(self):
        for root in self:
            root.name = root.id
            root.parent_id = self.browse(root.id[:-1] if len(root.id) > 1 else False)
