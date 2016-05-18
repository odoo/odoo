# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class RecruitmentSettings(models.TransientModel):
    _name = 'hr.recruitment.config.settings'
    _inherit = ['res.config.settings']

    module_document = fields.Selection(selection=[
            (0, "Do not manage CVs and motivation letter"),
            (1, 'Allow the automatic indexation of resumes')
            ], string='Resumes')
