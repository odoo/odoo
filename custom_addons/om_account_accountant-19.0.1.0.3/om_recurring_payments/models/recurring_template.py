from dateutil.relativedelta import relativedelta
from odoo import models, fields, api


class AccountRecurringTemplate(models.Model):
    _name = 'account.recurring.template'
    _description = 'Recurring Template'
    _rec_name = 'name'

    name = fields.Char('Name', required=True)
    journal_id = fields.Many2one('account.journal', 'Journal', required=True)
    recurring_period = fields.Selection(selection=[('days', 'Days'),
                                                   ('weeks', 'Weeks'),
                                                   ('months', 'Months'),
                                                   ('years', 'Years')], store=True, required=True)
    description = fields.Text('Description')
    state = fields.Selection(selection=[('draft', 'Draft'),
                                        ('done', 'Done')], default='draft', string='Status')
    journal_state = fields.Selection(selection=[('draft', 'Un Posted'),
                                                ('posted', 'Posted')],
                                     required=True, default='draft', string='Generate Journal As')
    recurring_interval = fields.Integer('Recurring Interval', default=1, required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)

    @api.depends('date_begin', 'date_end')
    def _compute_next_call(self):
        for rec in self:
            exec_date = rec.date_begin + relativedelta(days=rec.recurring_interval)
            if exec_date <= rec.date_end:
                rec.next_call = exec_date
            else:
                rec.state = 'done'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_done(self):
        for rec in self:
            rec.state = 'done'


