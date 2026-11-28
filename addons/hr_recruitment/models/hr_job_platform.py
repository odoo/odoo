# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import email_normalize


class HrJobPlatform(models.Model):
    _name = 'hr.job.platform'
    _description = 'Job Platform'

    name = fields.Char(required=True)
    email = fields.Char(required=True, help="Applications received from this Email won't be linked to a contact."
                                            "There will be no email address set on the Applicant either.",
                        clean=lambda email: email_normalize(email) or email)
    regex = fields.Char(help="The regex facilitates to extract information from the subject or body "
                             "of the received email to autopopulate the Applicant's name field")

    _email_uniq = models.Constraint(
        'unique (email)',
        'The Email must be unique, this one already corresponds to another Job Platform.',
    )
