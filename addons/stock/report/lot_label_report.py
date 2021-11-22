# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.exceptions import UserError


def _prepare_data(env, data):
    if data.get('active_model') == 'stock.production.lot':
        quantity_by_lot = {env['stock.production.lot'].browse(int(p)): q for p, q in data.get('quantity_by_lot').items()}
    else:
        raise UserError(_('Lot/Serial model not defined, Please contact your administrator.'))
    layout_wizard = env['lot.label.layout'].browse(data.get('layout_wizard'))
    if not layout_wizard:
        return {}

    return {
        'quantity': quantity_by_lot,
        'rows': layout_wizard.rows,
        'columns': layout_wizard.columns,
        'page_numbers': (sum(quantity_by_lot.values()) - 1) // (layout_wizard.rows * layout_wizard.columns) + 1,
    }


class ReportLotLabel(models.AbstractModel):
    _name = 'report.stock.report_lotlabel'
    _description = 'Lot/Serial Label Report'

    def _get_report_values(self, docids, data):
        return _prepare_data(self.env, data)


class ReportLotLabelZpl(models.AbstractModel):
    _name = 'report.stock.report_lotlabel_zpl'
    _description = 'Lot/Serial Label Report ZPL'

    def _get_report_values(self, docids, data):
        return _prepare_data(self.env, data)


class ReportLotLabelDymo(models.AbstractModel):
    _name = 'report.stock.report_lotlabel_dymo'
    _description = 'Lot/Serial Label Report'

    def _get_report_values(self, docids, data):
        return _prepare_data(self.env, data)
