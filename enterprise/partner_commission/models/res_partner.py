# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResPartnerGrade(models.Model):
    _inherit = 'res.partner.grade'

    default_commission_plan_id = fields.Many2one(
        'commission.plan',
        'Default Commission Plan',
        help='The default commission plan used for this grade. Can be overwritten on the partner form.')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _default_commission_plan(self):
        return self.grade_id.default_commission_plan_id

    commission_plan_id = fields.Many2one('commission.plan', 'Commission Plan', default=_default_commission_plan, tracking=True)

    @api.onchange('grade_id')
    def _onchange_grade_id(self):
        self.commission_plan_id = self._default_commission_plan()
