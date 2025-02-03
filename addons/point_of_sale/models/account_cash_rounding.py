from odoo import api, models, _
from odoo.exceptions import ValidationError


class AccountCashRounding(models.Model):
    _name = 'account.cash.rounding'
    _inherit = ['account.cash.rounding', 'pos.load.mixin']

    @api.constrains('rounding', 'rounding_method', 'strategy')
    def _check_session_state(self):
        open_session = self.env['pos.session'].search([('config_id.rounding_method', 'in', self.ids), ('state', '!=', 'closed')], limit=1)
        if open_session:
            raise ValidationError(
                _("You are not allowed to change the cash rounding configuration while a pos session using it is already opened."))

    @api.model
    def _load_pos_data_domain(self, data):
        return [('id', '=', data['pos.config'][0]['rounding_method'])]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'rounding', 'rounding_method', 'strategy']
