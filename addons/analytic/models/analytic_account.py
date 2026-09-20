from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError
from odoo.tools import SQL, float_is_zero, groupby


class AccountAnalyticAccount(models.Model):
    _name = "account.analytic.account"
    _inherit = ["mixin.mail.thread"]
    _description = "Analytic Account"
    _order = "plan_id, name asc"
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of
    _rec_names_search = ["name", "code"]

    name = fields.Char(
        string="Analytic Account",
        translate=True,
        index="trigram",
        required=True,
        tracking=True,
    )
    code = fields.Char(
        string="Reference",
        index="btree",
        tracking=True,
    )
    active = fields.Boolean(
        default=True,
        tracking=True,
        help="Deactivate the account.",
    )
    plan_id = fields.Many2one(
        comodel_name="account.analytic.plan",
        index=True,
        required=True,
    )
    root_plan_id = fields.Many2one(  # noqa: E8529  plan_id.root_id is a non-stored compute over parent_path: there is no column to join
        comodel_name="account.analytic.plan",
        related="plan_id.root_id",
        string="Root Plan",
        store=True,
    )
    color = fields.Integer(
        related="plan_id.color",
        string="Color Index",
    )

    line_ids = fields.One2many(
        comodel_name="account.analytic.line",
        inverse_name="auto_account_id",  # magic link to the right column (plan) by using the context in the view
        string="Analytic Lines",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        index="btree_not_null",
        check_company=True,
        # use bypass_search_access to speed up name_search call
        bypass_search_access=True,
        tracking=True,
    )

    balance = fields.Monetary(compute="_compute_debit_credit_balance")
    debit = fields.Monetary(compute="_compute_debit_credit_balance")
    credit = fields.Monetary(compute="_compute_debit_credit_balance")

    currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Currency",
    )

    @api.constrains("company_id")
    def _check_company_consistency(self):
        for company, accounts in groupby(self, lambda account: account.company_id):
            if company and self.env["account.analytic.line"].sudo().search_count(  # noqa: E8507 - one query per company; accounts sharing one were merged above
                [
                    ("auto_account_id", "in", [account.id for account in accounts]),
                    "!",
                    ("company_id", "child_of", company.id),
                ],
                limit=1,
            ):
                raise UserError(
                    _(
                        "You can't change the company of an analytic account that already has analytic items! It's a recipe for an analytical disaster!"
                    )
                )

    @api.depends("code", "partner_id")
    def _compute_display_name(self):
        for analytic in self:
            name = analytic.name
            if analytic.code:
                name = f"[{analytic.code}] {name}"
            if analytic.partner_id.commercial_partner_id.name:
                name = f"{name} - {analytic.partner_id.commercial_partner_id.name}"
            analytic.display_name = name

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if "name" not in default:
            for account, vals in zip(self, vals_list, strict=False):
                vals["name"] = _("%s (copy)", account.name)
        return vals_list

    def copy_translations(self, new, excluded=()):
        # ``copy_data`` renames ``name`` in the duplicating user's language
        # only; without this the copy would keep the source record's exact
        # ``name`` in every other language.
        super().copy_translations(new, excluded=(*excluded, "name"))
        self._copy_translations_of_renamed_field(
            new, "name", lambda record, term: record.env._("%s (copy)", term)
        )

    def web_read(self, specification: dict[str, dict]) -> list[dict]:
        self_context = self
        if len(self) == 1:
            self_context = self.with_context(analytic_plan_id=self.plan_id.id)
        return super(AccountAnalyticAccount, self_context).web_read(specification)

    @api.depends("line_ids.amount")
    def _compute_debit_credit_balance(self):
        def convert(amount, from_currency):
            return from_currency._convert(
                from_amount=amount,
                to_currency=self.env.company.currency_id,
                company=self.env.company,
                date=fields.Date.today(),
            )

        domain = [("company_id", "in", [False] + self.env.companies.ids)]
        if self.env.context.get("from_date", False):
            domain.append(("date", ">=", self.env.context["from_date"]))
        if self.env.context.get("to_date", False):
            domain.append(("date", "<=", self.env.context["to_date"]))

        for plan, accounts in self.grouped("plan_id").items():
            if not plan:
                accounts.debit = accounts.credit = accounts.balance = 0
                continue
            credit_groups = self.env["account.analytic.line"]._read_group(  # noqa: E8507 - one query per plan: the plan names the column to group on
                domain=domain
                + [(plan._column_name(), "in", self.ids), ("amount", ">=", 0.0)],
                groupby=[plan._column_name(), "currency_id"],
                aggregates=["amount:sum"],
            )
            data_credit = defaultdict(float)
            for account, currency, amount_sum in credit_groups:
                data_credit[account.id] += convert(amount_sum, currency)

            debit_groups = self.env["account.analytic.line"]._read_group(  # noqa: E8507 - one query per plan: the plan names the column to group on
                domain=domain
                + [(plan._column_name(), "in", self.ids), ("amount", "<", 0.0)],
                groupby=[plan._column_name(), "currency_id"],
                aggregates=["amount:sum"],
            )
            data_debit = defaultdict(float)
            for account, currency, amount_sum in debit_groups:
                data_debit[account.id] += convert(amount_sum, currency)

            for account in accounts:
                account.debit = -data_debit.get(account.id, 0.0)
                account.credit = data_credit.get(account.id, 0.0)
                account.balance = account.credit - account.debit

    def _update_accounts_in_analytic_lines(self, new_fname, current_fname, accounts):
        if current_fname != new_fname:
            domain = [
                (new_fname, "not in", accounts.ids + [False]),
                (current_fname, "in", accounts.ids),
            ]
            if self.env["account.analytic.line"].sudo().search_count(domain, limit=1):
                list_view = self.env.ref(
                    "analytic.view_account_analytic_line_tree", raise_if_not_found=False
                )
                raise RedirectWarning(
                    message=_(
                        "Whoa there! Making this change would wipe out your current data. Let's avoid that, shall we?"
                    ),
                    action={
                        "res_model": "account.analytic.line",
                        "type": "ir.actions.act_window",
                        "domain": domain,
                        "target": "new",
                        "views": [(list_view and list_view.id, "list")],
                    },
                    button_text=_("See them"),
                )
            self.env.cr.execute(
                SQL(
                    """
                UPDATE account_analytic_line
                   SET %(new_fname)s = %(current_fname)s,
                       %(current_fname)s = NULL
                 WHERE %(current_fname)s = ANY(%(account_ids)s)
                """,
                    new_fname=SQL.identifier(new_fname),
                    current_fname=SQL.identifier(current_fname),
                    account_ids=accounts.ids,
                )
            )
            self.env["account.analytic.line"].invalidate_model()

    def write(self, vals):
        if vals.get("plan_id"):
            new_fname = (
                self.env["account.analytic.plan"].browse(vals["plan_id"])._column_name()
            )
            for plan, accounts in self.grouped("plan_id").items():
                current_fname = plan._column_name()
                self._update_accounts_in_analytic_lines(
                    new_fname, current_fname, accounts
                )
        return super().write(vals)

    def _perform_analytic_distribution(
        self, distribution, amount, unit_amount, lines, obj, additive=False
    ):
        """
        Redistributes the analytic lines to match the given distribution:
            - For account_ids where lines already exist, the amount and unit_amount of these lines get updated,
              lines where the updated amount becomes zero get unlinked.
            - For account_ids where lines don't exist yet, the line values to create them are returned,
              lines where the amount becomes zero are not included.

        :param distribution:    the desired distribution to match the analytic lines to
        :param amount:          the total amount to distribute over the analytic lines
        :param unit_amount:     the total unit amount (will not be distributed)
        :param lines:           the (current) analytic account lines that need to be matched to the new distribution
        :param obj:             the object on which _prepare_analytic_line_values(account_id, amount, unit_amount) will be
                                called to get the template for the values of new analytic line objects
        :param additive:        if True, the unit_amount and (distributed) amount get added to the existing lines

        :returns: a list of dicts containing the values for new analytic lines that need to be created
        :rtype:   list
        """
        if not distribution:
            lines.unlink()
            return []

        # Does this: {'15': 40, '14,16': 60} -> { account(15): 40, account(14,16): 60 }
        distribution = {
            self.env["account.analytic.account"]
            .browse(map(int, ids.split(",")))
            .exists(): percentage
            for ids, percentage in distribution.items()
        }

        plans = self.env["account.analytic.plan"]
        plans = sum(plans._get_all_plans(), plans)
        line_columns = [p._column_name() for p in plans]

        lines_to_link = []
        distribution_on_each_plan = {}
        total_percentages = {}

        for accounts, percentage in distribution.items():
            for plan in accounts.root_plan_id:
                total_percentages[plan] = total_percentages.get(plan, 0) + percentage

        for existing_aal in lines:
            # The accounts this line already names, one plan column at a time.
            # `distribution` is keyed by the whole recordset, so the union has to
            # be built before it can be looked up.
            accounts = self.env["account.analytic.account"].union(
                *(existing_aal[column] for column in line_columns)
            )
            existing_aal = existing_aal.sudo()
            if accounts in distribution:
                # Update the existing AAL for this account
                percentage = distribution[accounts]
                new_amount = 0
                new_unit_amount = unit_amount
                for account in accounts:
                    plan = account.root_plan_id
                    new_amount = plan._get_distribution_amount(
                        amount,
                        percentage,
                        total_percentages[plan],
                        distribution_on_each_plan,
                    )
                if additive:
                    new_amount += existing_aal.amount
                    new_unit_amount += existing_aal.unit_amount
                currency = accounts[0].currency_id or obj.company_id.currency_id
                if float_is_zero(new_amount, precision_rounding=currency.rounding):
                    existing_aal.unlink()
                else:
                    existing_aal.amount = new_amount
                    existing_aal.unit_amount = new_unit_amount
                # Prevent this distribution from being applied again
                del distribution[accounts]
            else:
                # Delete the existing AAL if it is no longer present in the new distribution
                existing_aal.unlink()
        # Create new lines from remaining distributions
        for accounts, percentage in distribution.items():
            if not accounts:
                continue
            account_field_values = {}
            for account in accounts:
                plan = account.root_plan_id
                new_amount = plan._get_distribution_amount(
                    amount,
                    percentage,
                    total_percentages[plan],
                    distribution_on_each_plan,
                )
                account_field_values[account.plan_id._column_name()] = account.id
            # `accounts[0]`, as in the update branch above: `account` here is
            # whichever plan's account the loop happened to end on, so the two
            # branches rounded against different currencies for the same
            # distribution key.
            currency = accounts[0].currency_id or obj.company_id.currency_id
            if not float_is_zero(new_amount, precision_rounding=currency.rounding):
                lines_to_link.append(
                    obj._prepare_analytic_line_values(
                        account_field_values, new_amount, unit_amount
                    )
                )
        return lines_to_link
