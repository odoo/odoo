from odoo import models, fields

class BioEditorWizard(models.TransientModel):
    _name = 'mi_website_ext.bio_editor.wizard'
    _description = 'Editor de Biografía'

    bio = fields.Text(string='Biografía')

    def action_save(self):
        # Guardamos la biografía en el usuario actual
        user = self.env.user
        user.write({'bio': self.bio})  # asegúrate que este campo exista
        return {'type': 'ir.actions.act_window_close'}
