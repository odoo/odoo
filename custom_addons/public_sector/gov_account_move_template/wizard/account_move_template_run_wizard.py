import ast

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountMoveTemplateRunWizard(models.TransientModel):
    _name = "account.move.template.run.wizard"
    _description = "Run Journal Entry Template Wizard"

    template_id = fields.Many2one("account.move.template", required=True, readonly=True)
    date = fields.Date(required=True, default=fields.Date.context_today)
    ref = fields.Char()
    amount = fields.Monetary(currency_field="currency_id")
    company_id = fields.Many2one(
        "res.company",
        related="template_id.company_id",
        readonly=True,
    )
    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True)
    preview_line_ids = fields.One2many(
        "account.move.template.run.wizard.line",
        "wizard_id",
        compute="_compute_preview_lines",
        string="Preview Lines",
    )

    def _safe_eval_amount(self, expression, total, lines):
        if not expression:
            raise ValidationError(_("Computed expression is empty."))
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as exc:
            raise ValidationError(_("Invalid computed expression syntax: %s") % expression) from exc
        for node in ast.walk(tree):
            if isinstance(
                node,
                (
                    ast.Call,
                    ast.Attribute,
                    ast.Import,
                    ast.ImportFrom,
                    ast.Lambda,
                    ast.FunctionDef,
                    ast.ClassDef,
                    ast.Global,
                    ast.Nonlocal,
                    ast.With,
                    ast.Try,
                    ast.While,
                    ast.For,
                ),
            ):
                raise ValidationError(_("Unsafe operation in computed expression."))
        return eval(compile(tree, "<amount_expr>", "eval"), {"__builtins__": {}}, {"total": total, "lines": lines})

    @api.depends("amount", "template_id", "template_id.line_ids")
    def _compute_preview_lines(self):
        for wizard in self:
            wizard.preview_line_ids.unlink()
            command_vals = []
            running = {}
            for line in wizard.template_id.line_ids.sorted(key=lambda l: (l.sequence, l.id)):
                if line.amount_type == "fixed":
                    resolved = line.amount_fixed
                elif line.amount_type == "percent":
                    resolved = (line.amount_percent / 100.0) * wizard.amount
                else:
                    resolved = wizard._safe_eval_amount(line.amount_expr, wizard.amount, running)
                resolved = wizard.currency_id.round(resolved)
                running[line.sequence] = resolved
                command_vals.append(
                    (
                        0,
                        0,
                        {
                            "sequence": line.sequence,
                            "name": line.name,
                            "account_id": line.account_id.id,
                            "partner_id": line.partner_id.id,
                            "analytic_distribution": line.analytic_distribution,
                            "move_type": line.move_type,
                            "amount": resolved,
                        },
                    )
                )
            wizard.preview_line_ids = command_vals

    def _prepare_move_vals(self):
        self.ensure_one()
        debit_sum = 0.0
        credit_sum = 0.0
        line_cmds = []
        for line in self.preview_line_ids.sorted(key=lambda l: (l.sequence, l.id)):
            debit = line.amount if line.move_type == "dr" else 0.0
            credit = line.amount if line.move_type == "cr" else 0.0
            debit_sum += debit
            credit_sum += credit
            line_cmds.append(
                (
                    0,
                    0,
                    {
                        "name": line.name,
                        "account_id": line.account_id.id,
                        "partner_id": line.partner_id.id,
                        "analytic_distribution": line.analytic_distribution or {},
                        "debit": debit,
                        "credit": credit,
                    },
                )
            )
        delta = self.currency_id.round(debit_sum - credit_sum)
        if delta != 0.0:
            raise UserError(_("Template preview is unbalanced by %s.") % delta)
        return {
            "journal_id": self.template_id.journal_id.id,
            "date": self.date,
            "ref": self.ref or self.template_id.ref,
            "company_id": self.company_id.id,
            "line_ids": line_cmds,
        }

    def action_create_move(self):
        self.ensure_one()

        # -- MONTH-END CLOSE INTEGRATION ----------------------------------
        # This wizard is the primary interface for the structured
        # close calendar. Recommended templates to create:
        #   - Monthly Depreciation
        #   - Prepaid Expense Amortization
        #   - Accrued Revenue Recognition
        #   - Intercompany Allocation
        # Each template is run once per close cycle, producing
        # a fully documented, auditable journal entry.
        # Pair with gov_account_lock_date_update.action_apply()
        # to lock the period immediately after all templates
        # have been run.
        # ---------------------------------------------------------------

        move = self.env["account.move"].create(self._prepare_move_vals())
        move.action_post()
        return {
            "type": "ir.actions.act_window",
            "name": _("Journal Entry"),
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": move.id,
            "target": "current",
        }

    def action_create_move_draft(self):
        self.ensure_one()
        move = self.env["account.move"].create(self._prepare_move_vals())
        return {
            "type": "ir.actions.act_window",
            "name": _("Journal Entry"),
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": move.id,
            "target": "current",
        }


class AccountMoveTemplateRunWizardLine(models.TransientModel):
    _name = "account.move.template.run.wizard.line"
    _description = "Template Run Preview Line"

    wizard_id = fields.Many2one("account.move.template.run.wizard", ondelete="cascade")
    sequence = fields.Integer()
    name = fields.Char()
    account_id = fields.Many2one("account.account")
    partner_id = fields.Many2one("res.partner")
    analytic_distribution = fields.Json()
    move_type = fields.Selection([("dr", "Debit"), ("cr", "Credit")])
    currency_id = fields.Many2one(related="wizard_id.currency_id", readonly=True)
    amount = fields.Monetary(currency_field="currency_id")

