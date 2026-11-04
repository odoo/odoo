from odoo import models, api


class IrUiView(models.Model):
    _name = 'ir.ui.view'
    _inherit = ['ir.ui.view', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name']

    def _load_pos_data(self, data):
        fields = self._load_pos_data_fields(data['pos.config']['data'][0]['id'])
        return {
            'data': self.env.ref('base.view_partner_form').sudo().read(fields),
            'fields': fields
        }
