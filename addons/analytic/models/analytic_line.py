from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class AccountAnalyticLine(models.Model):
    _name = "account.analytic.line"
    _inherit = ["mixin.analytic.plan.fields"]
    _description = "Analytic Line"
    _order = "date desc, id desc"
    _check_company_auto = True

    name = fields.Char(
        string="Description",
        required=True,
    )
    date = fields.Date(
        default=fields.Date.context_today,
        index=True,
        required=True,
    )
    amount = fields.Monetary(
        default=0.0,
        required=True,
    )
    unit_amount = fields.Float(
        string="Quantity",
        default=0.0,
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        check_company=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        default=lambda self: self.env.context.get("user_id", self.env.user.id),
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        readonly=True,
        required=True,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Currency",
        compute_sudo=True,
        readonly=True,
    )
    category = fields.Selection(
        selection=[("other", "Other")],
        default="other",
    )
    from_last_fiscal_year = fields.Boolean(
        export_string_translation=False,
        search="_search_from_last_fiscal_year",
        store=False,
        exportable=False,
    )
    analytic_distribution = fields.Json(
        compute="_compute_analytic_distribution",
        inverse="_inverse_analytic_distribution",
    )
    analytic_precision = fields.Integer(
        default=lambda self: self.env["decimal.precision"].get_precision(
            "Percentage Analytic"
        ),
        store=False,
    )

    def _compute_analytic_distribution(self):
        for line in self:
            line.analytic_distribution = {line._get_distribution_key(): 100}

    def _inverse_analytic_distribution(self):
        empty_account = dict.fromkeys(self._get_plan_fnames(), False)
        to_create_vals = []
        for line in self:
            final_distribution = self.env["mixin.analytic"]._merge_distribution(
                {line._get_distribution_key(): 100},
                line.analytic_distribution or {},
            )
            if not final_distribution:
                continue
            amount_fname = line._split_amount_fname()
            vals_list = [
                {amount_fname: line[amount_fname] * percent / 100}
                | empty_account
                | {
                    account.plan_id._column_name(): account.id
                    for account in self.env["account.analytic.account"].browse(
                        int(aid) for aid in account_ids.split(",")
                    )
                }
                for account_ids, percent in final_distribution.items()
            ]

            line.write(vals_list[0])
            to_create_vals += [line.copy_data(vals)[0] for vals in vals_list[1:]]
        if to_create_vals:
            self.create(to_create_vals)
            self.env.user._bus_send(
                "simple_notification",
                {
                    "type": "success",
                    "message": self.env._(
                        "%s analytic lines created", len(to_create_vals)
                    ),
                },
            )

    def _split_amount_fname(self):
        return "amount"

    def _search_from_last_fiscal_year(self, operator, value):
        fiscalyear_date_range = self.env.company.compute_fiscalyear_dates(
            fields.Date.today()
        )
        return [
            ("date", ">=", fiscalyear_date_range["date_from"] - relativedelta(years=1))
        ]

    # ------------------------------------------------------------------
    # Keeping the accounts' balances coherent
    #
    # `account.analytic.account.debit`, `credit` and `balance` aggregate these
    # rows with `_read_group`, and declare `@api.depends("line_ids.amount")`.
    # That declaration cannot fire: `line_ids`'s inverse is `auto_account_id`,
    # a context-dependent compute with no column, so the ORM has no trigger
    # from a line back to the accounts it names.  Measured before this hook --
    # one account, one line, all three reads in one transaction:
    #
    #     create line, amount -100   -> debit 100   (first read, nothing cached)
    #     write  line, amount -250   -> debit 100   (250 after invalidate_all)
    #     create a second line, -10  -> debit 250   (260 after invalidate_all)
    #     unlink that second line    -> debit 260   (250 after invalidate_all)
    #
    # so every write after the first read was invisible, in either direction.
    # The dependency the compute really has is on rows of *this* model, which
    # `@api.depends` has no way to spell, so the line states it instead.
    # ------------------------------------------------------------------

    #: what `_compute_debit_credit_balance` reads off a line, besides the plan
    #: columns: the amount it sums, the currency and company it converts
    #: through, and the date its `from_date`/`to_date` context filters on.
    _ACCOUNT_BALANCE_TRIGGERS = frozenset(
        {"amount", "company_id", "currency_id", "date"}
    )
    _ACCOUNT_BALANCE_FIELDS = ("balance", "credit", "debit")

    def _get_balance_accounts(self):
        """Every analytic account these lines name, across every plan.

        `mapped`, not `self[fname]`: this runs over whole batches, and reading
        a field off a multi-record set goes through `check_singleton`.
        """
        accounts = self.env["account.analytic.account"]
        for fname in self._get_plan_fnames():
            accounts |= self.mapped(fname)
        return accounts

    def _notify_balance_accounts(self, accounts):
        if not accounts:
            return
        # Both halves are needed: `invalidate_recordset` drops the stale
        # values, `modified` tells whatever depends on them.  `modified` alone
        # only walks the dependents of the three fields, never the fields.
        accounts.invalidate_recordset(self._ACCOUNT_BALANCE_FIELDS)
        accounts.modified(self._ACCOUNT_BALANCE_FIELDS)

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._notify_balance_accounts(lines._get_balance_accounts())
        return lines

    def write(self, vals):
        if not self._ACCOUNT_BALANCE_TRIGGERS.isdisjoint(vals) or not set(
            self._get_plan_fnames()
        ).isdisjoint(vals):
            # The accounts on both sides of the write: repointing a line at
            # another account leaves the old one holding a stale sum too.
            accounts = self._get_balance_accounts()
            res = super().write(vals)
            self._notify_balance_accounts(accounts | self._get_balance_accounts())
            return res
        return super().write(vals)

    def unlink(self):
        accounts = self._get_balance_accounts()
        res = super().unlink()
        self._notify_balance_accounts(accounts)
        return res
