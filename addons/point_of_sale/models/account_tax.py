from odoo import api, models
from odoo.exceptions import UserError

from ..tools import debug_log as dbg


class AccountTax(models.Model):
    _name = "account.tax"
    _inherit = ["account.tax", "mixin.pos.load"]

    def write(self, vals):
        forbidden_fields = {
            "amount_type",
            "amount",
            "type_tax_use",
            "tax_group_id",
            "price_include",
            "price_include_override",
            "include_base_amount",
            "is_base_affected",
        }
        if forbidden_fields & set(vals.keys()) and self.ids:
            dbg.logic.debug(
                "account.tax.write %s touches %s: checking open pos sessions",
                dbg.rec(self),
                sorted(forbidden_fields & set(vals)),
            )
            self.env["pos.order.line"].flush_model(["tax_ids"])
            self.env.cr.execute(
                """
                SELECT 1
                FROM account_tax_pos_order_line_rel AS rel
                JOIN pos_order_line AS line ON line.id = rel.pos_order_line_id
                JOIN pos_order AS o ON o.id = line.order_id
                JOIN pos_session AS s ON s.id = o.session_id
                WHERE rel.account_tax_id = ANY(%s)
                  AND o.company_id = ANY(%s)
                  AND s.state != 'closed'
                LIMIT 1
                """,
                [list(self.ids), list(self.company_ids.ids)],
            )
            if self.env.cr.fetchone():
                raise UserError(
                    self.env._(
                        "It is forbidden to modify a tax used in a POS order not posted. "
                        "You must close the POS sessions before modifying the tax."
                    )
                )
        return super().write(vals)

    def _get_used_tax_ids(self, tax_ids):
        used_taxes = super()._get_used_tax_ids(tax_ids)
        remaining_ids = tax_ids - used_taxes
        if remaining_ids:
            self.env["pos.order.line"].flush_model(["tax_ids"])
            self.env.cr.execute(
                """
                SELECT DISTINCT account_tax_id
                FROM account_tax_pos_order_line_rel
                WHERE account_tax_id = ANY(%s)
                """,
                [list(remaining_ids)],
            )
            used_taxes.update(tax[0] for tax in self.env.cr.fetchall())
            dbg.logic.debug(
                "account.tax used check: %d unresolved by account, %d used by pos lines",
                len(remaining_ids),
                len(used_taxes),
            )
        return used_taxes

    @api.model
    def _load_pos_data_domain(self, data, config):
        return self.env["account.tax"]._check_company_domain(config.company_id.id)

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            "id",
            "name",
            "price_include",
            "include_base_amount",
            "is_base_affected",
            "has_negative_factor",
            "amount_type",
            "children_tax_ids",
            "amount",
            "company_ids",
            "sequence",
            "tax_group_id",
            "fiscal_position_ids",
        ]
