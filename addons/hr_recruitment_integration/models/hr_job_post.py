# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class JobPost(models.Model):
    _name = "hr.job.post"
    _description = "Job Post"

    job_id = fields.Many2one('hr.job', string="Job")
    provider = fields.Char(string="Provider")
    status = fields.Selection(
        [('success', 'Success'),
         ('failure', 'Failure'),
         ('expired', 'Expired')
        ], string='Status')
    valid_until = fields.Date()
    url = fields.Char(string="Job URL")
