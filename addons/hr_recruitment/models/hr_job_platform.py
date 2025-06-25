# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import email_normalize


class JobPlatform(models.Model):
    _name = "hr.job.platform"
    _description = 'Job Platforms'

    name = fields.Char(required=True)
    email = fields.Char(required=True, help="Applications received from this Email won't be linked to a contact."
                                            "There will be no email address set on the Applicant either.")
    regex = fields.Char(help="The regex facilitates to extract information from the subject or body "
                             "of the received email to autopopulate the Applicant's name field")

    _sql_constraints = [
        ('email_uniq', 'unique (email)', "The Email must be unique, this one already corresponds to another Job Platform."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals['email']:
                vals['email'] = email_normalize(vals['email']) or vals['email']
        platforms = super().create(vals_list)
        return platforms

    def write(self, vals):
        if vals.get('email'):
            vals['email'] = email_normalize(vals['email']) or vals['email']
        return super().write(vals)
