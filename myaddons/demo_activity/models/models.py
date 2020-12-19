from odoo import models, fields, api

class DemoActivity(models.Model):
    _name = "demo.activity"
    _description = "Demo Activity"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='name', required=True)
    employee_id = fields.Many2one(
        'hr.employee', string="Employee", required=True)

    def button_activity_schedule(self):
        self.activity_schedule(
            'demo_activity.mail_act_approval',
            user_id = self.sudo().employee_id.user_id.id,
            note = 'my note',
            summary = 'my summary')

    def button_activity_feedback(self):
        self.activity_feedback(
            ['demo_activity.mail_act_approval'])

    def button_activity_unlink(self):
        self.activity_unlink(
            ['demo_activity.mail_act_approval'])

    def test(self):
        print(111)
    def test2(self):
        print(222)
