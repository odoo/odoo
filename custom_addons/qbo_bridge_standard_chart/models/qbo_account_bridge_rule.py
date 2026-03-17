from odoo import api, fields, models


class QboAccountBridgeRule(models.Model):
    _inherit = "qbo.account.bridge.rule"

    standard_account_id = fields.Many2one(
        "qbo.standard.account",
        string="Standard chart account",
        ondelete="set null",
    )

    @api.onchange("standard_account_id")
    def _onchange_standard_account_id(self):
        for rec in self:
            rec._apply_standard_account()

    @api.model_create_multi
    def create(self, vals_list):
        prepared_vals = [self._prepare_standard_account_vals(vals) for vals in vals_list]
        return super().create(prepared_vals)

    def write(self, vals):
        vals = self._prepare_standard_account_vals(vals)
        return super().write(vals)

    def _prepare_standard_account_vals(self, vals):
        vals = dict(vals)
        standard_account_id = vals.get("standard_account_id")
        if standard_account_id:
            standard_account = self.env["qbo.standard.account"].browse(standard_account_id)
            vals.update(
                {
                    "canonical_code": standard_account.code,
                    "canonical_name": standard_account.description,
                    "canonical_account_type": standard_account.odoo_account_type,
                },
            )
        return vals

    def _apply_standard_account(self):
        self.ensure_one()
        if not self.standard_account_id:
            return
        self.canonical_code = self.standard_account_id.code
        self.canonical_name = self.standard_account_id.description
        self.canonical_account_type = self.standard_account_id.odoo_account_type
