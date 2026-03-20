from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError


class AccountCashRounding(models.Model):
    _name = 'account.cash.rounding'
    _inherit = ['account.cash.rounding', 'pos.load.mixin']

    @api.ondelete(at_uninstall=False)
    def _unlink_except_pos_config(self):
        if self.env['pos.config'].search_count([('rounding_method', 'in', self.ids)], limit=1):
            raise UserError(_('You cannot delete a rounding method that is used in a Point of Sale configuration.'))

    @api.constrains('rounding', 'rounding_method', 'strategy')
    def _check_session_state(self):
        open_session = self.env['pos.session'].search([('config_id.rounding_method', 'in', self.ids), ('state', '!=', 'closed')], limit=1)
        if open_session:
            raise ValidationError(
                _("You are not allowed to change the rounding configuration while a pos session using it is already opened. Make sure to close all open pos session before proceeding."))

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('id', '=', config.rounding_method.id)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'rounding', 'rounding_method', 'strategy']
