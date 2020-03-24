from odoo import _, fields, models
from odoo.exceptions import UserError


class ModelName (models.TransientModel):
    _name = 'pos_unbalanced_force_close.wizard'
    _description = 'Wizard: Confirmation of force close'

    def _default_session(self):
        return self.env['pos.session'].browse(self._context.get('active_id'))

    session_id = fields.Many2one('pos.session', default=_default_session)
    force_close_unbalanced_difference = fields.Float('Difference', related='session_id._force_close_unbalanced_difference')

    def force_close(self):
        if not all([
            self.session_id.config_id.difference_debit_account,
            self.session_id.config_id.difference_credit_account,
        ]):
            raise UserError(_('Difference Debit Account and Difference Credit account must be defined in the POS configuration.'))
        self.session_id.with_context(force_close_unbalanced=True).action_pos_session_closing_control()

    def set_rescue(self):
        if self.session_id.rescue:
            raise UserError(_('Session already in "Recovery" modus.'))

        self.session_id.rescue = True
