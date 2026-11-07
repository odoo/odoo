# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_cn_edi_drawer = fields.Char(related='company_id.l10n_cn_edi_drawer', readonly=False)
    l10n_cn_edi_is_ready = fields.Boolean(compute='_compute_l10n_cn_edi_is_ready')

    l10n_cn_edi_yunshui_identity_code = fields.Char(
        related='company_id.l10n_cn_edi_yunshui_identity_code',
        readonly=False,
        groups='base.group_system',
    )
    l10n_cn_edi_yunshui_platform_code = fields.Char(
        related='company_id.l10n_cn_edi_yunshui_platform_code',
        readonly=False,
        groups='base.group_system',
    )
    l10n_cn_edi_yunshui_gateway = fields.Selection(
        related='company_id.l10n_cn_edi_yunshui_gateway',
        readonly=False,
    )
    l10n_cn_edi_yunshui_username = fields.Char(
        related='company_id.l10n_cn_edi_yunshui_username',
        readonly=False,
        groups='base.group_system',
    )
    l10n_cn_edi_yunshui_password = fields.Char(
        related='company_id.l10n_cn_edi_yunshui_password',
        readonly=False,
        groups='base.group_system',
    )
    l10n_cn_edi_yunshui_region_code = fields.Char(
        related='company_id.l10n_cn_edi_yunshui_region_code',
        readonly=False,
        groups='base.group_system',
    )

    @api.depends('company_id')
    def _compute_l10n_cn_edi_is_ready(self):
        for settings in self:
            settings.l10n_cn_edi_is_ready = settings.company_id._l10n_cn_edi_is_ready()

    def action_l10n_cn_edi_yunshui_test_connection(self):
        self.ensure_one()
        self.company_id._l10n_cn_edi_get_client().test_connection()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': self.env._("Yunshui accepted the credentials of %(company)s.", company=self.company_id.name),
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    def action_l10n_cn_edi_yunshui_login(self):
        self.ensure_one()
        return self.company_id._l10n_cn_edi_action_login()
