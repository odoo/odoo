from odoo import fields, models

class AdmissionLead(models.Model):
    _name = 'admission.lead'
    _description = 'Admission Applicant'
    _order = 'id desc'

    student_name = fields.Char(required=True)
    email = fields.Char()
    phone = fields.Char()
    stage_id = fields.Many2one(
        'admission.stage', string='Stage',
        default=lambda self: self.env['admission.stage'].search(
            [], limit=1, order='sequence'))
    program_id = fields.Many2one('university.program', string='Program')
    active = fields.Boolean(default=True)
    lost_reason = fields.Char(string='Rejection Reason')

    def action_set_won(self):
        won_stage = self.env['admission.stage'].search(
            [('is_won', '=', True)], limit=1)
        for rec in self:
            rec.stage_id = won_stage or rec.stage_id

    def action_set_lost(self):
        for rec in self:
            rec.active = False