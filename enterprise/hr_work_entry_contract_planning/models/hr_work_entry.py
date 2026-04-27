# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    planning_slot_id = fields.Many2one('planning.slot', groups='hr.group_hr_user', index='btree_not_null')

    def _get_planning_duration(self, date_start, date_stop):
        '''
        If the interval(date_start, date_stop) is equal to the planning_slot's interval, return the slot's allocated hours.
        If the interval(date_start, date_stop) is a subset of the planning_slot's interval,
        a new (non saved) planning_slot will be created to compute the duration according to planning rules.
        If the interval(date_start, date_stop) is not fully inside of the planning_slot's interval the behaviour is undefined

        :return: The real duration according to the planning app
        :rtype: number
        '''
        self.ensure_one()
        date_start = date_start or self.date_start
        date_stop = date_stop or self.date_stop

        if (self.planning_slot_id.start_datetime == date_start and\
            self.planning_slot_id.end_datetime == date_stop):
            return self.planning_slot_id.allocated_hours
        else:
            new_slot = self.env['planning.slot'].new({
                **self.planning_slot_id.read(['employee_id', 'company_id', 'allocated_percentage', 'resource_id'])[0],
                **{
                    'start_datetime': date_start,
                    'end_datetime': date_stop,
                },
            })
            return new_slot.allocated_hours

    def _get_duration_batch(self):
        res = dict()
        super_we = self.env['hr.work.entry']
        for we in self:
            if we.planning_slot_id:
                res[we.id] = we._get_planning_duration(False, False)
            else:
                super_we |= we
        res.update(super(HrWorkEntry, super_we)._get_duration_batch())
        return res

    def _get_work_duration(self, date_start, date_stop):
        """
        When using the duration of the planning slot, we also need to simulate the duration
         using the slot's percentage if set instead of simply using the work entry's dates.
        """
        if self.planning_slot_id:
            return self._get_planning_duration(date_start, date_stop)
        return super()._get_work_duration(date_start, date_stop)
