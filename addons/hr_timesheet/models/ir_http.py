# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        """ The widget 'timesheet_uom' needs to know which UoM conversion factor and which javascript
            widget to apply, depending on the current company.
        """
        result = super().session_info()
        if self.env.user._is_internal():
            company_ids = self.env.user.company_ids

            for company in company_ids:
                uom_day = self.env.ref('uom.product_uom_day', raise_if_not_found=False)
                uom_hour = self.env.ref('uom.product_uom_hour', raise_if_not_found=False)
                encode_uom = uom_hour if self.env['ir.config_parameter'].sudo().get_str('hr_timesheet.timesheet_encode_method', 'hours') == 'hours' else uom_day
                result["user_companies"]["allowed_companies"][company.id].update({
                    "timesheet_uom_id": encode_uom.id,
                    "timesheet_uom_factor": company.project_time_mode_id._compute_quantity(
                        1.0,
                        encode_uom,
                        round=False
                    ),
                })
            result["uom_ids"] = self.get_timesheet_uoms()
        return result

    @api.model
    def get_timesheet_uoms(self):
        uom_day = self.env.ref('uom.product_uom_day', raise_if_not_found=False)
        uom_hour = self.env.ref('uom.product_uom_hour', raise_if_not_found=False)
        timesheet_encode_method = uom_hour if self.env['ir.config_parameter'].sudo().get_str('hr_timesheet.timesheet_encode_method', 'hours') == 'hours' else uom_day
        company_ids = self.env.user.company_ids
        uom_ids = timesheet_encode_method | company_ids.mapped('project_time_mode_id')
        return {
            uom.id:
                {
                    'id': uom.id,
                    'name': uom.name,
                    'timesheet_widget': uom.timesheet_widget,
                } for uom in uom_ids
        }
