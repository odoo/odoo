from odoo import models
from odoo.tools import _


class IrActionsServer(models.Model):
    _inherit = 'ir.actions.server'

    def action_open_documents_server_action_view(self):
        self.check_access('read')
        return {
            'context': {
                'default_model_id': self.env['ir.model']._get_id('documents.document'),
                'default_update_path': 'tag_ids',
            },
            'display_name': _('Server Actions'),
            'domain': [('model_name', '=', 'documents.document')],
            'help': """
                <div style="width:650px;">
                    <p class="d-none">%s</p>
                    <img class="w-100 w-md-75" src="/documents/static/img/documents_server_action.svg"/>
                </div>
            """ % _('No server actions found for Documents!'),
            'res_model': 'ir.actions.server',
            'target': 'current',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')]
        }
