# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class HelpdeskTicketConvertWizard(models.TransientModel):
    _inherit = 'helpdesk.ticket.convert.wizard'

    def _default_project_id(self):
        tickets_to_convert = self._get_tickets_to_convert()
        projects = tickets_to_convert.project_id
        if len(projects) == 1:
            return projects.id
        elif len(projects) > 1:
            return projects.sorted('sequence')[0].id
        else:
            return False
