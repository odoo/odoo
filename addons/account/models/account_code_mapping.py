from odoo import fields, models, api
from odoo.tools import Query
from odoo.exceptions import UserError


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
                companies = companies.sorted(lambda c: (c.sequence, c.name))

                records = self._get_records(
                    (account_id, company.id)
                    for account_id in account_ids
                    for company in companies
                )
                return records._as_query()

        raise NotImplementedError

    @api.model
    def _get_records(self, record_keys):
        """ Get a recordset of code mappings for the given (account_id, company_id) record keys.

            :param keys: an iterable of (account_id, company_id) record keys
            :return: a recordset of code mappings corresponding to the record keys, in the same order.
        """
        record_keys = list(record_keys)
        existing_records = self.env.cache.get_records(self, self._fields['account_id'])
        record_id_by_key = {(record.account_id.id, record.company_id.id): record.id for record in existing_records}

        missing_keys = [
            record_key
            for record_key in record_keys
            if record_key not in record_id_by_key
        ]

        max_existing_id = max(existing_records.ids, default=0)
        new_record_ids = range(max_existing_id + 1, max_existing_id + len(missing_keys) + 1)
        new_code_mappings = self.browse(new_record_ids)

        self.env.cache.update(new_code_mappings, self._fields['account_id'], [account_id for account_id, _ in missing_keys])
        self.env.cache.update(new_code_mappings, self._fields['company_id'], [company_id for _, company_id in missing_keys])

        record_id_by_key.update(zip(missing_keys, new_record_ids))

        return self.browse(record_id_by_key[key] for key in record_keys)

    @api.depends('account_id.code')
    def _compute_code(self):
        for record in self:
            account = record.account_id.with_company(record.company_id._origin)
            record.code = account.code

    def _inverse_code(self):
        for record in self:
            allowed_company_ids = (record.company_id | self.env.companies).ids
            record.account_id.with_context({'allowed_company_ids': allowed_company_ids}).code = record.code

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if len(vals.keys() & {'account_id', 'company_id', 'code'}) != 3:
                raise UserError(self.env._("When modifying a code mapping for an account, you must specify both the company and the code for that company."))

            account = self.env['account.account'].browse(vals['account_id'])
            account.with_company(vals['company_id']).code = vals['code']

        return self._get_records((vals['account_id'], vals['company_id']) for vals in vals_list)
