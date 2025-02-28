from odoo import models

class FleetAttachmentPreview(models.Model):
    _inherit = 'ir.attachment'

    def action_preview_attachment(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s/%s' % (self.id, self.name),
            'target': 'new',
        }
