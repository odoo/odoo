# # Part of Odoo. See LICENSE file for full copyright and licensing details.

# from odoo import fields, models


# class ResCompany(models.Model):
#     _inherit = 'res.company'

#     public_holiday_name = fields.Char(compute="_compute_public_holiday", store=False)

#     def _compute_public_holiday(self):
#         today = fields.Date.today()
#         for record in self:
#             holiday = self.env['resource.calendar.leaves'].sudo().search([
#                 ('resource_id', '=', False),
#                 ('company_id', '=', record.id),
#                 ('date_from', '<=', today),
#                 ('date_to', '>=', today),
#             ], limit=1)
#             record.public_holiday_name = holiday.name if holiday else False
