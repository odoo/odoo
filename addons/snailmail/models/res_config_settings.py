from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    snailmail_color = fields.Boolean(
        related="company_id.snailmail_color",
        string="Print In Color",
        readonly=False,
    )
    snailmail_cover = fields.Boolean(
        related="company_id.snailmail_cover",
        string="Add a Cover Page",
        readonly=False,
    )
    snailmail_duplex = fields.Boolean(
        related="company_id.snailmail_duplex",
        string="Print Both sides",
        readonly=False,
    )

    snailmail_cover_readonly = fields.Boolean(compute="_compute_cover_readonly")

    def _is_layout_cover_required(self):
        return self.external_report_layout_id in {
            self.env.ref(f"web.external_layout_{layout}")
            for layout in ("boxed", "bold", "striped")
        }

    @api.onchange("external_report_layout_id")
    def _onchange_layout(self):
        for record in self:
            if record._is_layout_cover_required():
                record.company_id.snailmail_cover = True

    @api.depends("external_report_layout_id")
    def _compute_cover_readonly(self):
        for record in self:
            record.snailmail_cover_readonly = self._is_layout_cover_required()
