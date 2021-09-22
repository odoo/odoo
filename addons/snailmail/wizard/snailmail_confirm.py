# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SnailmailConfirm(models.AbstractModel):
    _name = 'snailmail.confirm'
    _description = 'Snailmail Confirm'

    model_name = fields.Char()

    @api.model
    def show_warning(self):
        return not self.env['ir.config_parameter'].sudo().get_param('%s.warning_shown' % self._name, False)

    def action_open(self):
        view = self.env.ref('snailmail.snailmail_confirm_view')
        return {
            'name': _('Snailmail'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': self._name,
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': self.id,
            'context': self.env.context
        }

    def action_confirm(self):
        self.env['ir.config_parameter'].sudo().set_param('%s.warning_shown' % self._name, True)
        self._confirm()
        return self._continue()

    def action_cancel(self):
        self.env['ir.config_parameter'].sudo().set_param('%s.warning_shown' % self._name, True)
        return self._continue()

    """
    Called whether the user confirms or cancels posting the letter, e.g. to continue the action
    """
    def _continue(self):
        pass

    """
    Called only when the user confirms sending the letter
    """
    def _confirm(self):
        pass
