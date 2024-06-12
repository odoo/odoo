from odoo import models, fields, api

class DeleteConfirmationWizard(models.TransientModel):
    _name = 'delete.confirmation.wizard'
    _description = 'Delete Confirmation Wizard'

    name = fields.Char('Name')

    def action_confirm_delete(self):
        context = self._context
        active_id = context.get('active_id')
        if active_id:
            if context.get('active_model', False) == 'product.template':
                product = self.env['product.template'].browse(active_id)
                product.action_delete_all_tiktok_img()
            if context.get('active_model', False) == 'product.product':
                product = self.env['product.product'].browse(active_id)
                product.action_delete_all_tiktok_var_img()
