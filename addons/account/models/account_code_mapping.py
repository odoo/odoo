from odoo import fields, models, api
from odoo.tools import Query


class AccountCodeMapping(models.Model):
    # This model is used purely for UI, to display the account codes for each company.
    # It is not stored in DB. Instead, records are only populated in cache by the
    # `_search` override when accessing the One2many on `account.account`.

    _name = 'account.code.mapping'
    _description = "Mapping of account codes per company"
    _auto = False
    _table_query = '0'

    account_id = fields.Many2one(
        comodel_name='account.account',
        string="Account",
        store=False,
        # suppress warning about field not being searchable (due to being used in depends);
        # searching is actually implemented in the `_search` override.
        search=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company",
        store=False,
    )
    code = fields.Char(
        string="Code",
        compute='_compute_code',
        inverse='_inverse_code',
    )

    def browse(self, ids=()):
        if isinstance(ids, str):
            ids = (ids,)
        return super().browse(ids)

    def _search(self, domain, offset=0, limit=None, order=None) -> Query:
        # This method will populate this model's records in cache when the `code_mapping_ids`
        # One2many on `account_account` is accessed. Any existing records that correspond to the
        # search domain will be returned, and additional ones will be created in cache as needed.
        match domain:
            case [('account_id', 'in', account_ids)]:
                companies = self.env.user.company_ids
                existing_code_mappings = self.env.cache.get_records(self, self._fields['account_id']).filtered(
                    lambda m: m.account_id.id in account_ids and m.company_id in companies
                )
                keys = {(m.account_id.id, m.company_id.id) for m in existing_code_mappings}
                missing_keys = [
                    (account_id, company_id)
                    for account_id in account_ids
                    for company_id in companies.ids
                    if (account_id, company_id) not in keys
                ]
                max_existing_id = max(existing_code_mappings.ids, default=0)
                new_code_mappings = self.browse(range(max_existing_id + 1, max_existing_id + len(missing_keys) + 1))

                self.env.cache.update(new_code_mappings, self._fields['account_id'], [account_id for account_id, _ in missing_keys])
                self.env.cache.update(new_code_mappings, self._fields['company_id'], [company_id for _, company_id in missing_keys])

                mappings = existing_code_mappings | new_code_mappings
                return mappings.sorted(lambda m: (m.account_id.id, m.company_id.sequence, m.company_id.name))._as_query()
        raise NotImplementedError

    @api.depends('account_id.code')
    def _compute_code(self):
        for record in self:
            account = record.account_id.with_company(record.company_id._origin)
            record.code = account.code

    def _inverse_code(self):
        for record in self:
            record.account_id.with_company(record.company_id._origin).code = record.code
