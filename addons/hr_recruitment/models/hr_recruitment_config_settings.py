# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class RecruitmentSettings(models.TransientModel):
    _name = 'hr.recruitment.config.settings'
    _inherit = ['res.config.settings', 'fetchmail.config.settings']

    module_document = fields.Selection(selection=[
            (0, "Do not manage CVs and motivation letter"),
            (1, 'Allow the automatic indexation of resumes')
            ], string='Resumes',
            help='Manage your CV\'s and motivation letter related to all applicants.\n'
                            '-This installs the module document_ftp. This will install the knowledge management  module in order to allow you to search using specific keywords through  the content of all documents (PDF, .DOCx...)')
