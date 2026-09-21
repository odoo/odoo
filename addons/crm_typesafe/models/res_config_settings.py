# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    typesafe_api_key = fields.Char(
        'TypeSafe API Key', config_parameter='crm.typesafe.api_key',
        help="Server-side key used to call TypeSafe's System One API (https://app.typesafe.ai)")
    typesafe_provider = fields.Selection([
        ('typesafe', 'TypeSafe (api.typesafe.ai)'),
        ('vercel', 'Vercel AI Gateway'),
        ('openrouter', 'OpenRouter'),
    ], string='TypeSafe Provider', default='typesafe', config_parameter='crm.typesafe.provider',
        help="Where requests are sent. The API key must belong to the selected provider.")
    typesafe_model = fields.Char(
        'TypeSafe Model', config_parameter='crm.typesafe.model',
        help="Leave empty to use the provider's default Jev model (jev-latest, or typesafe-ai/jev on Vercel AI Gateway)")
    typesafe_qualify_auto = fields.Selection([
        ('auto', 'Qualify leads automatically'),
        ('manual', 'Qualify leads manually'),
    ], string='Qualify leads automatically', default='auto', config_parameter='crm.typesafe.qualify.setting')

    @api.model
    def get_values(self):
        values = super().get_values()
        cron = self.sudo().with_context(active_test=False).env.ref('crm_typesafe.ir_cron_lead_qualification', raise_if_not_found=False)
        values['typesafe_qualify_auto'] = 'auto' if cron and cron.active else 'manual'
        return values

    def set_values(self):
        super().set_values()
        cron = self.sudo().with_context(active_test=False).env.ref('crm_typesafe.ir_cron_lead_qualification', raise_if_not_found=False)
        if cron and cron.active != (self.typesafe_qualify_auto == 'auto'):
            cron.active = self.typesafe_qualify_auto == 'auto'
