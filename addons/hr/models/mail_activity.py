# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    technical_usage = fields.Selection(selection_add=[
        ('hr_expiring_contract', 'Expiring Contract'),
        ('hr_expiring_work_permit', 'Expiring Work Permit')
    ])
