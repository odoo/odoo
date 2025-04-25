from odoo import models, fields, api

class SummaryReview(models.Model):
    _name = 'summary.review'
    _description = 'Daily Summary Review'

    summary_id = fields.Many2one('daily.summary', string="Summary", required=True)
    reviewer_id = fields.Many2one('hr.employee', string="Reviewer", required=True)
    remarks = fields.Text(string="Remarks")
    rating = fields.Selection([
        ('1', 'Poor'),
        ('2', 'Fair'),
        ('3', 'Good'),
        ('4', 'Very Good'),
        ('5', 'Excellent')
    ], string="Rating")
    date_reviewed = fields.Datetime(string="Reviewed On", default=fields.Datetime.now)
    approved_by_id = fields.Many2one('hr.employee', string="Approved by")
    approved_on = fields.Datetime(string="Approved On")

    def create(self, vals):
        record = super(SummaryReview, self).create(vals)
        if record.summary_id:
            record.summary_id.reviewed = True
        return record
