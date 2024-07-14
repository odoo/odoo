# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DocumentsFolder(models.Model):
    _inherit = 'documents.folder'

    product_template_ids = fields.One2many('product.template', 'template_folder_id')

    @api.constrains('company_id')
    def _check_company_is_products_company(self):
        for folder in self:
            if folder.product_template_ids and folder.product_template_ids.company_id:
                different_company_templates = folder.product_template_ids.filtered_domain(self.env['product.template']._check_company_domain(self.company_id))
                if not different_company_templates:
                    continue
                if len(different_company_templates) == 1:
                    template = different_company_templates[0]
                    message = _('This workspace should remain in the same company as the "%s" product for which it is a template. Please update the company of the "%s" product, or leave the company of this workspace empty.', template.name, template.name),
                else:
                    lines = [f"- {template.name}" for template in different_company_templates]
                    message = _('This workspace should remain in the same company as the following products for which it is a template:\n%s\n\nPlease update the company of those products, or leave the company of this workspace empty.', '\n'.join(lines)),
                raise UserError(message)
