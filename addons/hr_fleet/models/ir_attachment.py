# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def action_preview_attachment(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s/%s' % (self.id, self.name),
            'target': 'new',
        }

    @api.model
    def action_attach_uploads(self, attachment_ids):
        """ Attach the uploaded files to the record the view is opened for,
        given by `default_res_model` and `default_res_id` in the context.
        """
        record = self.env[self.env.context['default_res_model']].browse(
            self.env.context['default_res_id'],
        )
        self.browse(attachment_ids).write({'res_model': record._name, 'res_id': record.id})
