# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class DeferredReportCustomHandler(models.AbstractModel):
    _inherit = 'account.deferred.report.handler'

    @api.model
    def _get_select(self):
        return super()._get_select() + ["account_move_line.vehicle_id AS vehicle_id"]

    @api.model
    def _get_grouping_keys_deferred_lines(self, filter_already_generated=False):
        res = super()._get_grouping_keys_deferred_lines()
        if filter_already_generated:
            res += ('vehicle_id',)
        return res

    @api.model
    def _get_grouping_keys_deferral_lines(self):
        res = super()._get_grouping_keys_deferral_lines()
        res += ('vehicle_id',)
        return res

    @api.model
    def _get_current_key_totals_dict(self, lines_per_key, sign):
        totals = super()._get_current_key_totals_dict(lines_per_key, sign)
        totals['vehicle_id'] = lines_per_key[0]['vehicle_id']
        return totals
