from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

from ..tools import debug_log as dbg


class PosDetailsWizard(models.TransientModel):
    _name = "pos.details.wizard"
    _description = "Point of Sale Details Report"

    def _default_start_date(self):
        values = self.env["pos.session"]._read_group(
            [
                ("config_id", "!=", False),
                ("start_at", ">", self.env.cr.now() - timedelta(days=2)),
            ],
            groupby=["config_id"],
            aggregates=["start_at:max"],
        )
        return min(
            (start_at for _config, start_at in values), default=self.env.cr.now()
        )

    start_date = fields.Datetime(
        default=_default_start_date,
        required=True,
    )
    end_date = fields.Datetime(
        default=fields.Datetime.now,
        required=True,
    )
    pos_config_ids = fields.Many2many(
        comodel_name="pos.config",
        relation="pos_detail_configs",
        default=lambda s: s.env["pos.config"].search([]),
    )

    @api.onchange("start_date")
    def _onchange_start_date(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            self.end_date = self.start_date

    @api.onchange("end_date")
    def _onchange_end_date(self):
        if self.end_date and self.start_date and self.end_date < self.start_date:
            self.start_date = self.end_date

    def action_print_report(self):
        self.check_singleton()
        if self.end_date < self.start_date:
            raise UserError(self.env._("The end date must not precede the start date."))
        data = {
            "date_start": self.start_date,
            "date_stop": self.end_date,
            "config_ids": self.pos_config_ids.ids,
        }
        dbg.lifecycle.debug("[wizard:details] print %s", data)
        return self.env.ref("point_of_sale.sale_details_report").report_action(
            [], data=data
        )
