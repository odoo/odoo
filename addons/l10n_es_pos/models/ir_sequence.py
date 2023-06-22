from odoo import _, api, models
from odoo.exceptions import UserError


class IrSequence(models.Model):
    _inherit = "ir.sequence"

    @api.constrains("prefix", "code")
    def check_simplified_invoice_unique_prefix(self):
        if self._context.get("copy_pos_config"):
            return
        for sequence in self.filtered(lambda x: x.code == "pos.config.simplified_invoice"):
            if (
                self.search_count(
                    [
                        ("code", "=", "pos.config.simplified_invoice"),
                        ("prefix", "=", sequence.prefix),
                    ]
                )
                > 1
            ):
                raise UserError(
                    _(
                        "There is already a simplified invoice "
                        "sequence with that prefix and it should be "
                        "unique."
                    )
                )

    def _sanitize_prefix(self, initial_prefix):
        prefix = initial_prefix
        ith = 0
        while self.env["ir.sequence"].search_count([("prefix", "=", prefix)]):
            ith += 1
            prefix = f"{initial_prefix}{ith}-"
        return prefix
