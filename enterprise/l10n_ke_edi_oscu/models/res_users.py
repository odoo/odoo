# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Users(models.Model):
    _inherit = 'res.users'

    l10n_ke_oscu_company_ids = fields.One2many('res.company', compute='_compute_l10n_ke_oscu_company_ids')

    @api.depends('company_ids')
    def _compute_l10n_ke_oscu_company_ids(self):
        for user in self:
            user.l10n_ke_oscu_company_ids = user.company_ids.filtered(lambda c: c.l10n_ke_oscu_is_active)

    def action_l10n_ke_create_branch_user(self):
        for user in self:
            for company in user.l10n_ke_oscu_company_ids:
                error, _data, _dummy = company._l10n_ke_call_etims('saveBhfUser', {
                    'userId': user.id,
                    'userNm': user.login,
                    'pwd':    'test',
                    'useYn':  'Y',
                    'regrId': self.env.user.id,
                    'regrNm': self.env.user.name,
                    'modrId': self.env.user.id,
                    'modrNm': self.env.user.name,
                })
                if error:
                    raise UserError(error)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'sticky': False,
                'message': _("User successfully registered"),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
