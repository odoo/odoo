# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _action_confirm(self):
        res = super()._action_confirm()
        projects_without_template = self.env['project.project']
        for order in self:
            sols_per_project = defaultdict(lambda: self.env['sale.order.line'])
            for sol in order.order_line:
                if sol.project_id:
                    sols_per_project[sol.project_id] |= sol

            for project, sols in sols_per_project.items():
                if not project.use_documents or project.documents_folder_id:
                    continue
                template_folders = sols.product_template_id.template_folder_id
                project_sudo = project.sudo()

                if len(template_folders) > 1:
                    project_sudo.documents_folder_id = template_folders.sudo()._copy_and_merge({
                        'name': project.name,
                        'company_id': project.company_id.id,
                    })
                    # It is necessary to set the parent after the copy to avoid
                    # infinite recursion issues.
                    project_sudo.documents_folder_id.parent_folder_id = self.env.ref('documents_project.documents_project_folder').id
                elif len(template_folders) == 1:
                    project_sudo.documents_folder_id = template_folders.sudo().copy({
                        'name': project.name,
                        'company_id': project.company_id.id,
                        'parent_folder_id': template_folders.parent_folder_id.id,
                    })
                else:
                    projects_without_template |= project

        projects_without_template._create_missing_folders()
        return res
