# ©  2015-2020 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


from odoo import api, fields, models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    @api.model
    def _update_available_quantity(
        self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, in_date=None
    ):
        res = super(StockQuant, self)._update_available_quantity(
            product_id, location_id, quantity, lot_id, package_id, owner_id, in_date
        )

        return res


class StockMove(models.Model):
    _inherit = "stock.move"

    def write(self, vals):
        date_fields = {"date", "date_expected"}
        use_date = self.env.context.get("force_period_date", False)
        if date_fields.intersection(vals):
            if not use_date:

                for move in self:
                    today = fields.Date.today()
                    if "date" in vals:
                        if move.date_expected.date() < today and move.date_expected < vals["date"]:
                            vals["date"] = move.date_expected
                        if move.date.date() < today and move.date < vals["date"]:
                            vals["date"] = move.date
                        move.move_line_ids.write({"date": vals["date"]})
                        # move.quant_ids.write({'in_date': vals['date']})

                    # if 'date_expected' in vals:
                    #     if isinstance(vals['date_expected'], str):  # de unde ajunge aici cu string ?
                    #         vals['date_expected'] = fields.Datetime.to_datetime(vals['date_expected'])
                    #     move_date = vals.get('date', move.date)
                    #     if move_date.date() < today and move_date < vals['date_expected']:
                    #         vals['date_expected'] = move_date
            else:

                if "date" in vals:
                    vals["date"] = use_date
                # if 'date_expected' in vals:
                #     vals['date_expected'] = use_date

        return super(StockMove, self).write(vals)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        return super(StockPicking, self.with_context(force_period_date=self.scheduled_date)).button_validate()

    def action_done(self):
        super(StockPicking, self).action_done()
        use_date = self.env.context.get("force_period_date", False)
        if use_date:
            self.write({"date": use_date, "date_done": use_date})
            self.move_lines.write({"date": use_date})  # 'date_expected': use_date,
            self.move_line_ids.write({"date": use_date})
