from odoo import fields, models, _
from odoo.exceptions import UserError, RedirectWarning

from .pos_urban_piper_request import UrbanPiperClient


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    urbanpiper_username = fields.Char(
        string='UrbanPiper Username',
        config_parameter='pos_urban_piper.urbanpiper_username',
        help='The username for the UrbanPiper account.'
    )
    urbanpiper_apikey = fields.Char(
        string='UrbanPiper API Key',
        config_parameter='pos_urban_piper.urbanpiper_apikey',
        help='The API key for accessing the UrbanPiper services.'
    )
    pos_urbanpiper_store_identifier = fields.Char(
        string='UrbanPiper Store Identifier',
        related='pos_config_id.urbanpiper_store_identifier',
        readonly=False,
        help='The POS ID associated with UrbanPiper.'
    )
    pos_urbanpiper_pricelist_id = fields.Many2one(
        'product.pricelist',
        related='pos_config_id.urbanpiper_pricelist_id',
        string='UrbanPiper Pricelist',
        help='The pricelist used for UrbanPiper orders.'
    )
    pos_urbanpiper_fiscal_position_id = fields.Many2one(
        'account.fiscal.position',
        related='pos_config_id.urbanpiper_fiscal_position_id',
        string='UrbanPiper Fiscal Position',
        help='The fiscal position used for UrbanPiper transactions.'
    )
    pos_urbanpiper_payment_methods_ids = fields.Many2many(
        'pos.payment.method',
        related='pos_config_id.urbanpiper_payment_methods_ids',
        string='Online Delivery Payment Methods',
        domain="[('is_delivery_payment', '=', True)]",
        help='The payment methods used for online delivery through UrbanPiper.'
    )
    pos_urbanpiper_last_sync_date = fields.Datetime(
        string='Last Sync on',
        related='pos_config_id.urbanpiper_last_sync_date',
        help='The date and time of the last synchronization with UrbanPiper.'
    )
    pos_urbanpiper_webhook_url = fields.Char(
        string='Urban Piper Webhook URL',
        related='pos_config_id.urbanpiper_webhook_url',
        help='Register webhook with Urbanpiper.',
        readonly=False
    )
    pos_urbanpiper_delivery_provider_ids = fields.Many2many(
        'pos.delivery.provider',
        related='pos_config_id.urbanpiper_delivery_provider_ids',
        string='Online Delivery Providers',
        help='The delivery providers used for online delivery through UrbanPiper.'
    )

    def urbanpiper_create_store(self):
        """
        Create the store in UrbanPiper.
        """
        self.pos_config_id._check_required_request_params()
        if not self.pos_config_id.company_id.city:
            msg = _('Your company %s needs to have a correct city in order create the store.', self.pos_config_id.company_id.name)
            action = {
                'view_mode': 'form',
                'res_model': 'res.company',
                'type': 'ir.actions.act_window',
                'res_id': self.pos_config_id.company_id.id,
                'views': [[self.env.ref('base.view_company_form').id, 'form']],
            }
            raise RedirectWarning(msg, action, _('Go to Company configuration'))
        up = UrbanPiperClient(self.pos_config_id)
        up.configure_webhook()
        response_json = up.request_store_create()
        return self.pos_config_id._urbanpiper_handle_response(response_json)

    def urbanpiper_sync_menu(self):
        """
        Sync the menu with UrbanPiper. This will update the menu items and categories in UrbanPiper.
        """
        self.pos_config_id._check_required_request_params()
        if not self.pos_config_id.urbanpiper_delivery_provider_ids:
            raise UserError(_('UrbanPiper Delivery Providers are required.'))
        for provider in self.pos_urbanpiper_delivery_provider_ids:
            if self.pos_config_id.company_id.country_id not in provider.available_country_ids:
                country_names = [country.name for country in provider.available_country_ids]
                raise UserError(
                    _('(%(provider_name)s) delivery is only available in the following countries: \n%(country_names)s',
                    provider_name=provider.name, country_names=', '.join(country_names))
                )
        up = UrbanPiperClient(self.pos_config_id)
        up.configure_webhook()
        response_json = up.request_sync_menu()
        return self.pos_config_id._urbanpiper_handle_response(response_json)

    def action_refresh_webhooks(self):
        """
        If a webhook already exists on Atlas, refresh it; otherwise, create a new one.
        and products become available for syncing again as fresh entries.
        """
        self.pos_config_id._reset_urbanpiper_product_linkages()
        self.pos_config_id._check_required_request_params()
        up = UrbanPiperClient(self.pos_config_id)
        response_json = up.request_refresh_webhooks()
        return self.pos_config_id._urbanpiper_handle_response(response_json)

    def action_flush_and_sync_menu(self):
        """
        Resets all existing UrbanPiper product linkages and performs a fresh menu sync.
        """
        self.ensure_one()
        self.pos_config_id._reset_urbanpiper_product_linkages()
        return self.with_context(flush=True).urbanpiper_sync_menu()
