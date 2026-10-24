# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    folder_layout_custom_header_height = fields.Integer(
        string="Custom Header Height",
        compute='_compute_folder_layout_custom_header_height',
        inverse='_inverse_folder_layout_custom_header_height',
    )

    def _compute_folder_layout_custom_header_height(self):
        config_param = self.env['ir.config_parameter'].sudo()
        for company in self:
            company.folder_layout_custom_header_height = 174
            if (val := config_param.get_param(f'web.res_company.{company.id}.folder_layout_custom_header_height')) and val.isdigit():
                company.folder_layout_custom_header_height = int(val)

    def _inverse_folder_layout_custom_header_height(self):
        config_param = self.env['ir.config_parameter'].sudo()
        for company in self:
            config_param.set_param(f'web.res_company.{company.id}.folder_layout_custom_header_height', company.folder_layout_custom_header_height or 174)
