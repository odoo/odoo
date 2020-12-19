# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EmployeePerformanceTran(models.TransientModel):
    _name = 'employee.performance.manage.review'
    _description = "批量提交审核"

    performance_ids = fields.Many2many('employee.performance.manage', 'performance_manage_review_list_rel',
                                       string=u'员工绩效管理')

    @api.model
    def submit_review(self):
        """
        批量提交审核
        :return:
        """
        self.ensure_one()
        self.performance_ids.write({'state': 'wait'})
        return {'type': 'ir.actions.act_window_close'}

    @api.model
    def default_get(self, fields):
        context = dict(self._context or {})
        view_type = context.get('view_type')
        active_ids = context.get('active_ids')
        if not active_ids:
            raise UserError("未选择要提交的记录！")
        result = super(EmployeePerformanceTran, self).default_get(fields)
        if 'performance_ids' in fields:
            result['performance_ids'] = [(6, 0, active_ids)]
        return result