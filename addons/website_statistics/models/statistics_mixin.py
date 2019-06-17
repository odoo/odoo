# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StatisticsMixin(models.AbstractModel):
    _name = 'statistics.mixin'
    _description = 'Statistics Mixin'

    statistics_ids = fields.One2many('statistics.statistics', 'res_id', string='Website Statistics', domain=lambda self: [('res_model', '=', self._name)], auto_join=True)

    def unlink(self):
        """ When removing a record, its statistics should be deleted too. """
        record_ids = self.ids
        result = super(StatisticsMixin, self).unlink()
        self.env['statistics.statistics'].sudo().search([('res_model', '=', self._name), ('res_id', 'in', record_ids)]).unlink()
        return result
