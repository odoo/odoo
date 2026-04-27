# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class L10nUsWorkerCompensation(models.Model):
    _name = 'l10n.us.worker.compensation'
    _description = "Worker's Compensation"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    category = fields.Char(string='Class', help='Risk category classification of the job position')
    subcategory = fields.Char(string='Sub-Class', help='Risk sub-category classification of the job position')

    composite_rate = fields.Float(
        digits=(5, 4),
        help="Total got by adding up the four rates involved in workers' compensation "
             "(Accident fund, Medical Aid fund, Stay at Work program, and Supplemental rate)")
    payroll_deduction = fields.Float(
        digits=(5, 4),
        help="Total deduction that employees are responsible for "
             "(Half of Medical Aid fund, Stay at Work program, and Supplemental rate)")
