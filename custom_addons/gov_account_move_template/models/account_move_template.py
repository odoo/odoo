import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountMoveTemplate(models.Model):
    _name = "account.move.template"
    _description = "Journal Entry Template"
    _order = "name asc"

    name = fields.Char(required=True)
    journal_id = fields.Many2one("account.journal", required=True, check_company=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    ref = fields.Char()
    active = fields.Boolean(default=True)
    line_ids = fields.One2many("account.move.template.line", "template_id", string="Lines")
    line_count = fields.Integer(compute="_compute_line_count")

    @api.depends("line_ids")
    def _compute_line_count(self):
        for template in self:
            template.line_count = len(template.line_ids)

    def action_run_wizard(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "gov_account_move_template.account_move_template_run_wizard_action"
        )
        action["context"] = {
            "default_template_id": self.id,
            "default_company_id": self.company_id.id,
            "default_ref": self.ref,
        }
        return action

    @api.constrains("line_ids", "line_ids.move_type", "line_ids.amount_type", "line_ids.amount_fixed")
    def _check_template_balanced(self):
        for template in self:
            fixed_lines = template.line_ids.filtered(lambda l: l.amount_type == "fixed")
            has_computed = any(l.amount_type == "computed" for l in template.line_ids)
            fixed_delta = 0.0
            for line in fixed_lines:
                sign = 1 if line.move_type == "dr" else -1
                fixed_delta += sign * line.amount_fixed
            if fixed_delta and not has_computed:
                _logger.warning(
                    "Template %s appears unbalanced with fixed-only lines (delta=%s).",
                    template.display_name,
                    fixed_delta,
                )

