from odoo import api, models


class IrModuleModule(models.Model):
    _name = 'ir.module.module'
    _inherit = ['pos.load.mixin', 'ir.module.module']

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'state']

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('name', '=', 'pos_settle_due')]
