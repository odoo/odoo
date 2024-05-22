# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Project(models.Model):
    _inherit = 'project.project'

    def _get_not_billed_timesheets(self):
        """ Get the timesheets not invoiced and the SOL has not manually been edited
            FIXME: [XBO] this change must be done in the _update_timesheets_sale_line_id
                rather than this method in master to keep the initial behaviour of this method.
        """
        return super(Project, self)._get_not_billed_timesheets() - self.mapped('timesheet_ids').filtered('is_so_line_edited')
