# -*- coding: utf-8 -*-
"""Additional Schedules wizard (SF Workflow 2 step 12).

When an order line spans N+1 identical weeks, the user creates the first Schedule
and then enters `Additional Schedules = N` to auto-duplicate the row across the
next N consecutive Mondays.  In Odoo we implement this as a TransientModel
launched from the Schedule form with a button.
"""
from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class MvScheduleAdditionalWizard(models.TransientModel):
    _name = 'mv.schedule.additional.wizard'
    _description = 'Additional Schedules Wizard'

    schedule_id = fields.Many2one(
        comodel_name='mv.schedules',
        string='Source Schedule',
        required=True,
        ondelete='cascade',
    )
    count = fields.Integer(
        string='Additional Weeks',
        required=True,
        default=1,
        help='Number of identical weekly Schedules to create immediately AFTER the source schedule.',
    )

    @api.constrains('count')
    def _check_count_positive(self):
        for w in self:
            if w.count is None or w.count < 1:
                raise ValidationError(_("Additional Schedules count must be at least 1."))
            if w.count > 156:  # 3 years of weeks — safety net
                raise ValidationError(_("Additional Schedules count looks too large (>156 weeks). Aborting."))

    def action_create_schedules(self):
        self.ensure_one()
        src = self.schedule_id
        if not src.week:
            raise UserError(_("Source Schedule has no Week set; cannot duplicate forward."))

        # Fields we copy verbatim (excluding identifiers + auto-computed)
        CARRY_FIELDS = {
            'deal_parent', 'rate', 'units_available', 'networks', 'cap',
            'max_per_day', 'priority', 'special', 'test', 'days_allowed',
        }
        defaults = {}
        for f in CARRY_FIELDS:
            if f not in src._fields:
                continue
            val = src[f]
            if src._fields[f].type == 'many2many':
                defaults[f] = [(6, 0, val.ids)] if val else False
            elif src._fields[f].type == 'many2one':
                defaults[f] = val.id if val else False
            else:
                defaults[f] = val

        created_ids = []
        current_monday = src.week
        for i in range(int(self.count)):
            current_monday = current_monday + timedelta(days=7)
            vals = dict(defaults)
            vals['week'] = current_monday
            created_ids.append(self.env['mv.schedules'].create(vals).id)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Created Schedules'),
            'res_model': 'mv.schedules',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created_ids)],
        }
