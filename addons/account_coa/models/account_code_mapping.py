from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import Query

# Must exceed any realistic res.company id: undersizing it silently decodes
# a packed id to the wrong account/company instead of raising.
COMPANY_OFFSET = 10**6


def _pack_mapping_id(account_id, company_id):
    if not 0 <= company_id < COMPANY_OFFSET:
        raise ValueError(
            f"Company id {company_id} does not fit the code-mapping id encoding "
            f"(must be < {COMPANY_OFFSET})."
        )
    return account_id * COMPANY_OFFSET + company_id


class AccountCodeMapping(models.Model):
    """Per-company code override for an account, keyed by a packed virtual id."""

    _name = "account.code.mapping"
    _description = "Mapping of account codes per company"
    _auto = False
    _table_query = "0"
    _search_visibility_fields = ()

    account_id = fields.Many2one(
        comodel_name="account.account",
        compute="_compute_account_id",
        search=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_company_id",
    )
    code = fields.Char(
        compute="_compute_code",
        inverse="_inverse_code",
    )

    @api.model_create_multi
    def create(self, vals_list):
        by_key: dict[tuple[int, int], dict] = {}
        for vals in vals_list:
            key = (vals.get("account_id", 0), vals["company_id"])
            if key not in by_key or vals.get("code"):
                by_key[key] = vals
        vals_list = list(by_key.values())

        mappings = self.browse(
            [
                _pack_mapping_id(vals["account_id"], vals["company_id"])
                for vals in vals_list
            ]
        )
        for mapping, vals in zip(mappings, vals_list, strict=True):
            mapping.code = vals["code"]
        return mappings

    def _search(self, domain, offset=0, limit=None, order=None, **kw) -> Query:
        account_ids = []

        def get_accounts(condition):
            if (
                not account_ids
                and condition.field_expr == "account_id"
                and condition.operator == "in"
            ):
                account_ids.extend(condition.value)
                return Domain(bool(condition.value))
            return condition

        remaining_domain = Domain(domain).map_conditions(get_accounts)
        if not account_ids:
            raise UserError(
                _(
                    "Account Code Mapping cannot be accessed directly. "
                    "It is designed to be used only through the Chart of Accounts."
                )
            )
        return (
            self.browse(
                [
                    _pack_mapping_id(account_id, company.id)
                    for account_id in account_ids
                    for company in self.env.user.with_context(
                        active_test=True
                    ).company_ids.sorted(lambda c: (c.sequence, c.name))
                ]
            )
            .filtered_domain(remaining_domain)
            ._as_query()
        )

    def _compute_account_id(self):
        for record in self:
            record.account_id = record._origin.id // COMPANY_OFFSET

    def _compute_company_id(self):
        for record in self:
            record.company_id = record._origin.id % COMPANY_OFFSET

    @api.depends("account_id.code")
    def _compute_code(self):
        for record in self:
            account = record.account_id.with_company(record.company_id._origin)
            record.code = account.code

    def _inverse_code(self):
        for record in self:
            record.account_id.with_company(record.company_id).write(
                {"code": record.code}
            )
