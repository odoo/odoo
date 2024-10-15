# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import hr_recruitment


class HrApplicant(hr_recruitment.HrApplicant):

    candidate_skill_ids = fields.One2many(related="candidate_id.candidate_skill_ids", readonly=False)
    skill_ids = fields.Many2many(related="candidate_id.skill_ids", readonly=False)
