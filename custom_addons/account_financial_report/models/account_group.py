# © 2018 Forest and Biomass Romania SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.tools import SQL


class AccountGroup(models.Model):
    _inherit = "account.group"

    group_child_ids = fields.One2many(
        comodel_name="account.group", inverse_name="parent_id", string="Child Groups"
    )
    level = fields.Integer(compute="_compute_level", recursive=True)
    account_ids = fields.One2many(
        comodel_name="account.account",
        compute="_compute_account_ids",
        string="Accounts",
        store=False,
    )
    compute_account_ids = fields.Many2many(
        "account.account",
        recursive=True,
        compute="_compute_group_accounts",
        string="Compute accounts",
        store=False,
    )
    complete_name = fields.Char(
        "Full Name", compute="_compute_complete_name", recursive=True
    )
    complete_code = fields.Char(
        "Full Code", compute="_compute_complete_code", recursive=True
    )

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        """Forms complete name of location from parent location to child location."""
        for group in self:
            if group.parent_id.complete_name:
                group.complete_name = f"{group.parent_id.complete_name}/{group.name}"
            else:
                group.complete_name = group.name

    @api.depends("code_prefix_start", "code_prefix_end")
    def _compute_account_ids(self):
        """Retrieves every account from `self`.
        In Odoo 18 the group_id on account is not stored so it raises
        an error the one2many account_ids with inverse name group_id."""
        group_ids = self.ids
        self.account_ids = self.env["account.account"]
        if not group_ids:
            return
        group_ids = SQL(",".join(map(str, group_ids)))
        results = self.env.execute_query(
            SQL(
                """
        SELECT
        agroup.id AS group_id,
        STRING_AGG(DISTINCT account.id::text, ', ') as account_ids
        FROM  account_group agroup
        inner join account_account account
        ON agroup.code_prefix_start <= LEFT(%(code_store)s->>agroup.company_id::text,
        char_length(agroup.code_prefix_start))
        AND agroup.code_prefix_end >= LEFT(%(code_store)s->>agroup.company_id::text,
        char_length(agroup.code_prefix_end))
        WHERE agroup.id IN (%(group_ids)s)
        GROUP BY agroup.id
            """,
                code_store=SQL.identifier("account", "code_store"),
                group_ids=group_ids,
            )
        )
        group_by_code = dict(results)
        if not group_by_code:
            return
        for record in self:
            if group_by_code.get(record.id, ""):
                record.account_ids = list(
                    map(int, group_by_code.get(record.id, "").split(", "))
                )

    @api.depends("code_prefix_start", "parent_id.complete_code")
    def _compute_complete_code(self):
        """Forms complete code of location from parent location to child location."""
        for group in self:
            if group.parent_id.complete_code:
                group.complete_code = (
                    f"{group.parent_id.complete_code}/{group.code_prefix_start}"
                )
            else:
                group.complete_code = group.code_prefix_start

    @api.depends("parent_id", "parent_id.level")
    def _compute_level(self):
        for group in self:
            if not group.parent_id:
                group.level = 0
            else:
                group.level = group.parent_id.level + 1

    @api.depends(
        "group_child_ids.compute_account_ids",
    )
    def _compute_group_accounts(self):
        for one in self:
            one.compute_account_ids = (
                one.account_ids | one.group_child_ids.compute_account_ids
            )
