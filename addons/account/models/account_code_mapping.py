from odoo import fields, models, api
from odoo.tools import Query


class AccountCodeMapping(models.Model):
    _name = 'account.code.mapping'
    _description = "Mapping of account codes per company"
    _auto = False
    _table_query = '0'

    account_id = fields.Many2one(
        comodel_name='account.account',
        string="Account",
        compute='_compute_self',
        # suppress warning about field not being searchable (due to being used in depends);
        # searching is actually implemented in the `_search` override.
        search=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company",
        compute='_compute_self',
    )
    code = fields.Char(
        string="Code",
        compute='_compute_self',
        inverse='_inverse_code',
    )
    is_required = fields.Boolean(compute='_compute_is_required')

    def browse(self, ids=()):
        if isinstance(ids, str):
            ids = (ids,)
        return super().browse(ids)

    def _search(self, domain, offset=0, limit=None, order=None) -> Query:
        match domain:
            case [('id', 'in', ids)]:
                return self.browse(sorted(ids))._as_query()
            case [('account_id', 'in', account_ids)]:
                self_ids = {
                    f'{account_id},{company.id}'
                    for company in self.env.companies
                    for account_id in account_ids
                }
                return self.browse(sorted(self_ids))._as_query()
        raise NotImplementedError

    def _compute_self(self):
        for record in self:
            (account_id, company_id) = record._origin.id.split(',')
            # If record is a NewId, then record.account_id and record.company_id should be too
            # in order to behave correctly in onchange.
            if isinstance(record.id, models.NewId):
                record.account_id = models.NewId(int(account_id))
                record.company_id = models.NewId(int(company_id))
            else:
                record.account_id = int(account_id)
                record.company_id = int(company_id)
        # Do this in a separate loop, so that prefetching can happen if needed
        for record in self:
            account = record.account_id.with_company(record.company_id._origin)
            record.code = account.code

    def _inverse_code(self):
        for record in self:
            record.account_id.with_company(record.company_id._origin).code = record.code

    @api.depends('account_id.company_ids')
    def _compute_is_required(self):
        for record in self:
            record.is_required = record.company_id in record.account_id.company_ids
