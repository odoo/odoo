# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailActivityScheduleSummary(models.TransientModel):
    _name = 'mail.activity.schedule.line'
    _description = 'Mail Activity Schedule Line'
    _order = 'line_date_deadline asc, id asc'
    _rec_name = 'activity_schedule_id'

    activity_schedule_id = fields.Many2one('mail.activity.schedule', string="Activity Schedule",
                                           required=True, ondelete='cascade')
    line_description = fields.Char("Line Description")
    line_date_deadline = fields.Date("Date Deadline")
    responsible_user_id = fields.Many2one('res.users', string="Responsible User")
