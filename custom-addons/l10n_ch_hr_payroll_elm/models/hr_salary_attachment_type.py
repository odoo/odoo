# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrSalaryAttachmentType(models.Model):
    _inherit = 'hr.salary.attachment.type'

    is_quantity = fields.Boolean(default=False, string="Is quantity ?")
