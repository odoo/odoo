# ©  2015-2018 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from odoo import api, fields, models


class StockImmediateTransfer(models.TransientModel):
    _inherit = "stock.immediate.transfer"

    date = fields.Datetime(string="Date")

    @api.model
    def default_get(self, fields_list):
        res = super(StockImmediateTransfer, self).default_get(fields_list)
        res["date"] = self.env.context.get("force_period_date", fields.Datetime.now())
        return res

    def process(self):
        self.pick_ids.write({"date": self.date, "date_done": self.date})
        return super(StockImmediateTransfer, self.with_context(force_period_date=self.date)).process()
