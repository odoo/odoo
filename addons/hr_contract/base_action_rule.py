# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.addons.base_action_rule.base_action_rule import get_datetime
from openerp.osv import fields, osv


class base_action_rule(osv.Model):
    """ Add resource and calendar for time-based conditions """
    _name = 'base.action.rule'
    _inherit = ['base.action.rule']

    _columns = {
        'trg_date_resource_field_id': fields.many2one(
            'ir.model.fields', 'Use employee work schedule',
            help='Use the user\'s working schedule.',
        ),
    }

    def _check_delay(self, cr, uid, action, record, record_dt, context=None):
        """ Override the check of delay to try to use a user-related calendar.
        If no calendar is found, fallback on the default behavior. """
        if action.trg_date_calendar_id and action.trg_date_range_type == 'day' and action.trg_date_resource_field_id:
            user = record[action.trg_date_resource_field_id.name]
            if user.employee_ids and user.employee_ids[0].contract_id \
                    and user.employee_ids[0].contract_id.working_hours:
                calendar = user.employee_ids[0].contract_id.working_hours
                start_dt = get_datetime(record_dt)
                resource_id = user.employee_ids[0].resource_id.id
                action_dt = self.pool['resource.calendar'].schedule_days_get_date(
                    cr, uid, calendar.id, action.trg_date_range,
                    day_date=start_dt, compute_leaves=True, resource_id=resource_id,
                    context=context
                )
                return action_dt
        return super(base_action_rule, self)._check_delay(cr, uid, action, record, record_dt, context=context)
