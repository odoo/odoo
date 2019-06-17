#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools

class StockForecastPeriod(models.TransientModel):
    _name = 'stock.forecast.period'
    _description = 'Change period'

    date_from = fields.Datetime('Date from', default=fields.Datetime.now)

    def set_date_from(self):
        ctx = {}
        ctx.update(self.env.context)
        ctx.update({'date_from': self.date_from.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)})
        view = self.env.ref('stock.view_move_forecast_qweb')
        return {
            'name': 'Stock Forecast',
            'type': 'ir.actions.act_window',
            'view_type': 'qweb',
            'view_mode': 'qweb',
            'res_model': 'stock.move',
            'views': [(view.id, 'qweb')],
            'view_id': view.id,
            'target': 'main',
            'context': ctx,
        }
