from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountSplitJournalItemWizard(models.TransientModel):
    _name = "account.split.journal.item.wizard"
    _description = "Split journal items into several journal items"

    line_ids = fields.Many2many(
        comodel_name="account.move.line",
        relation="account_split_journal_item_move_line_rel",
        column1="wizard_id",
        column2="line_id",
    )
    line_currency_id = fields.Many2one(comodel_name="res.currency")
    quantity = fields.Integer(string="Quantity")
    amount = fields.Monetary(string="Amount", currency_field="line_currency_id")
    account_id = fields.Many2one(comodel_name="account.account", string="Account")

    show_simple_wizard = fields.Boolean(compute="_compute_show_simple_wizard")

    @api.depends("quantity", "line_ids")
    def _compute_show_simple_wizard(self):
        for wizard in self:
            wizard.show_simple_wizard = wizard.quantity != 2 or len(wizard.line_ids) > 1

    @api.onchange("quantity")
    def _onchange_quantity(self):
        for wizard in self:
            if len(wizard.line_ids) == 1 and wizard.quantity:
                wizard.amount = abs(wizard.line_ids.balance) / wizard.quantity

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)

        if defaults.get("line_ids"):
            line_ids = self._fields["line_ids"].convert_to_cache(
                defaults["line_ids"], self
            )
            if lines := self.env["account.move.line"].browse(line_ids):
                if any(move.state != "draft" for move in lines.move_id):
                    raise UserError(
                        self.env._("Only journal items of draft entries can be split.")
                    )
                if len(lines) == 1:
                    defaults["quantity"] = (
                        int(lines.quantity) if lines.quantity > 1 else 2
                    )
                    defaults["line_currency_id"] = lines.currency_id.id
                    defaults["amount"] = abs(lines.balance) / defaults["quantity"]
                    defaults["account_id"] = lines.account_id.id
                else:
                    defaults["quantity"] = 2

        return defaults

    def split(self):
        self.check_singleton()

        if self.quantity <= 1:
            raise UserError(self.env._("The quantity must be greater than 1."))

        if len(self.line_ids) == 1 and self.quantity == 2:
            original_balance = abs(self.line_ids.balance)
            if not 0 < self.amount < original_balance:
                raise UserError(
                    self.env._(
                        "The split amount must be strictly between 0 and the "
                        "amount of the journal item being split."
                    )
                )

        container = {"records": self.line_ids.move_id}
        with (
            self.env["account.move"]._check_balanced(container),
            self.env["account.move"]._sync_dynamic_lines(container),
        ):
            new_lines_vals = []
            for line in self.line_ids:
                # Split the field the move actually reasons about, so the
                # invoice-side recomputations stay consistent.
                fname = (
                    "balance"
                    if line.move_id.move_type == "entry"
                    else "price_unit"
                    if not self.show_simple_wizard
                    else "quantity"
                )
                # Round the way the field itself would.
                convert_to_cache = line._fields[fname].convert_to_cache

                if not self.show_simple_wizard:
                    split_amount = convert_to_cache(
                        line[fname] * self.amount / abs(line.balance), line
                    )
                    orig_amount = convert_to_cache(line[fname] - split_amount, line)
                    vals_list = [
                        {fname: orig_amount, "account_id": line.account_id.id},
                        {fname: split_amount, "account_id": self.account_id.id},
                    ]
                else:
                    running_amount = line[fname]
                    vals_list = []
                    for i in range(self.quantity):
                        running_amount -= (
                            current_amount := convert_to_cache(
                                running_amount / (self.quantity - i), line
                            )
                        )
                        vals_list.append(
                            {fname: current_amount, "account_id": line.account_id.id}
                        )

                if fname == "balance":
                    # `copy_data` carries `amount_currency` from the source line,
                    # and `_sync_dynamic_lines` re-derives `balance` from it, so a
                    # `balance`-only override is silently dropped on the copies and
                    # every split part comes back with the original amount. Split
                    # both, keeping the line's own rate.
                    rate = line.amount_currency / line.balance if line.balance else 0.0
                    for split_vals in vals_list:
                        split_vals["amount_currency"] = line.currency_id.round(
                            split_vals["balance"] * rate
                        )

                line.write(vals_list[0])
                deferred_vals = {
                    deferred_fname: val
                    for deferred_fname in (
                        "deferred_start_date",
                        "deferred_end_date",
                    )
                    if (val := line[deferred_fname])
                }
                new_lines_vals.extend(
                    line.copy_data(vals | deferred_vals)[0] for vals in vals_list[1:]
                )

            self.env["account.move.line"].create(new_lines_vals)
