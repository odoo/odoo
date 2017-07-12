# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields

class resPartnerWarning(models.TransientModel):

    _name = 'res.partner.warning'

    def _default_warning(self):
        return self._context.get('warning')

    warning = fields.Char(string='warning', default=_default_warning, readonly=True)

    def action_continue(self):
        return getattr(self.env[self._context.get('active_model')].with_context(skip_warning=True).browse(self._context['active_id']),self._context.get('warning_button_action'))()
