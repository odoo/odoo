from odoo import api, fields, models
from odoo.db.schema import column_exists, create_column


class AccountMove(models.Model):
    _inherit = "account.move"

    website_id = fields.Many2one(
        comodel_name="website",
        compute="_compute_website_id",
        store=True,
        readonly=True,
        tracking=True,
        help="Website through which this invoice was created for eCommerce orders.",
    )

    def _auto_init(self):
        if not column_exists(self.env.cr, "account_move", "website_id"):
            create_column(self.env.cr, "account_move", "website_id", "int4")
        super()._auto_init()

    def preview_invoice(self):
        action = super().preview_invoice()
        if action["url"].startswith("/"):
            action["url"] = f"/@{action['url']}"
        return action

    @api.depends("partner_id")
    def _compute_website_id(self):
        for move in self:
            source_websites = move.line_ids.sale_line_ids.order_id.website_id
            if len(source_websites) == 1:
                move.website_id = source_websites
            else:
                move.website_id = False
