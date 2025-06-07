# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        """ The widget 'timesheet_uom' needs to know which UoM conversion factor and which javascript
            widget to apply, depending on the current company.
        """
        result = super(Http, self).session_info()
        if self.env.user._is_internal():
            company_ids = self.env.user.company_ids

            for company in company_ids:
                result["user_companies"]["allowed_companies"][company.id].update({
                    "timesheet_uom_id": company.timesheet_encode_uom_id.id,
                    "timesheet_uom_factor": company.project_time_mode_id._compute_quantity(
                        1.0,
                        company.timesheet_encode_uom_id,
                        round=False
                    ),
                })
            result["uom_ids"] = self.get_timesheet_uoms()
        return result

    @api.model
    def get_timesheet_uoms(self):
        company_ids = self.env.user.company_ids
        uom_ids = company_ids.mapped('timesheet_encode_uom_id') | \
                  company_ids.mapped('project_time_mode_id')
        return {
            uom.id:
                {
                    'id': uom.id,
                    'name': uom.name,
                    'rounding': uom.rounding,
                    'timesheet_widget': uom.timesheet_widget,
                } for uom in uom_ids
        }
