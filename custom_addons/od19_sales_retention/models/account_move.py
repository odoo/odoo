from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    od19_retention_id = fields.Many2one(
        "od19.sales.retention",
        string="Sales Retention",
        readonly=True,
        copy=False,
        index=True,
        help="Retention this hold/release entry belongs to.",
    )

    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        for move in posted.filtered(
            lambda move: move.move_type in ("out_invoice", "out_refund")
        ):
            lines = self.env["od19.contract.billing.line"].search(
                [("invoice_id", "=", move.id)]
            )
            for line in lines:
                if line.od19_retention_rate and not line.od19_retention_id:
                    line._od19_create_retention()
        return posted
