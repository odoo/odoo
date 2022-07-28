# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random

from odoo import models
from odoo.tools import populate


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    def _populate(self, size):
        analytic_lines = super()._populate(size)
        random.sample(analytic_lines, random.randint(0, len(analytic_lines) // 2)).write({'category': 'manufacturing_order'})
        return analytic_lines

class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    _populate_dependencies = ['account.analytic.account']

    def _populate_factories(self):
        def get_analytic_account_id(values, counter, random):
            return random.choice(self.env['account.analytic.account'].search([])).id

        return super()._populate_factories() + [
            ('analytic_account_id', populate.compute(get_analytic_account_id))
        ]


class MrpProductionWorkcenterLineTime(models.Model):
    _inherit = 'mrp.workcenter.productivity'

    def _populate_factories(self):
        return super()._populate_factories() + [
            ('cost_already_recorded', populate.iterate([False, True]))
        ]

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def _populate_factories(self):
        return super()._populate_factories() + [
            ('extra_cost', populate.randfloat(0, 100))
        ]

class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    _populate_dependencies = ['account.analytic.account']

    def _populate_factories(self):
        def get_costs_hour_account_id(values, counter, random):
            if random.random() < 0.4:
                return random.choice(self.env['account.analytic.account'].search([])).id
            return False

        return super()._populate_factories() + [
            ('costs_hour_account_id', populate.compute(get_costs_hour_account_id))
        ]

class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    _populate_dependencies = ['account.analytic.line']

    def _populate_factories(self):
        def get_mo_analytic_account_line_id(values, counter, random):
            return random.choice(self.env['account.analytic.line'].search([])).id

        def get_wc_analytic_account_line_id(values, counter, random):
            return random.choice(self.env['account.analytic.line'].search([])).id

        return super()._populate_factories() + [
            ('mo_analytic_account_line_id', populate.compute(get_mo_analytic_account_line_id)),
            ('wc_analytic_account_line_id', populate.compute(get_wc_analytic_account_line_id))
        ]
