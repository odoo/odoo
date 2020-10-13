# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid
from werkzeug.urls import url_join

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AdyenAccount(models.Model):
    _inherit = 'adyen.account'

    store_ids = fields.One2many('adyen.store', 'adyen_account_id')
    terminal_ids = fields.One2many('adyen.terminal', 'adyen_account_id')

    @api.model
    def _sync_adyen_cron(self):
        self.env['adyen.terminal']._sync_adyen_terminals()
        super(AdyenAccount, self)._sync_adyen_cron()

    def action_order_terminal(self):
        if not self.store_ids:
            raise ValidationError(_('Please create a store first.'))

        store_uuids = ','.join(self.store_ids.mapped('store_uuid'))
        onboarding_url = self.env['ir.config_parameter'].sudo().get_param('adyen_platforms.onboarding_url')
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': url_join(onboarding_url, 'order_terminals?store_uuids=%s' % store_uuids),
        }


class AdyenStore(models.Model):
    _name = 'adyen.store'
    _inherit = ['adyen.address.mixin']
    _description = 'Adyen for Plaforms Store'

    adyen_account_id = fields.Many2one('adyen.account', ondelete='cascade')
    store_reference = fields.Char('Reference', default=lambda self: uuid.uuid4().hex)
    store_uuid = fields.Char('UUID', readonly=True) # Given by Adyen
    name = fields.Char('Name', required=True)
    phone_number = fields.Char('Phone Number', required=True)
    terminal_ids = fields.One2many('adyen.terminal', 'store_id', string='Payment Terminals', readonly=True)

    @api.model
    def create(self, values):
        adyen_store_id = super(AdyenStore, self).create(values)
        response = adyen_store_id.adyen_account_id._adyen_rpc('create_store', adyen_store_id._format_data())
        stores = response['accountHolderDetails']['storeDetails']
        created_store = next(store for store in stores if store['storeReference'] == adyen_store_id.store_reference)
        adyen_store_id.with_context(update_from_adyen=True).sudo().write({
            'store_uuid': created_store['store'],
        })
        return adyen_store_id

    def unlink(self):
        for store_id in self:
            store_id.adyen_account_id._adyen_rpc('close_stores', {
                'accountHolderCode': store_id.adyen_account_id.account_holder_code,
                'stores': [store_id.store_uuid],
            })
        return super(AdyenStore, self).unlink()

    def _format_data(self):
        return {
            'accountHolderCode': self.adyen_account_id.account_holder_code,
            'accountHolderDetails': {
                'storeDetails': [{
                    'storeReference': self.store_reference,
                    'storeName': self.name,
                    'merchantCategoryCode': '7999',
                    'address': {
                        'city': self.city,
                        'country': self.country_id.code,
                        'houseNumberOrName': self.house_number_or_name,
                        'postalCode': self.zip,
                        'stateOrProvince': self.state_id.code or None,
                        'street': self.street,
                    },
                    'fullPhoneNumber': self.phone_number,
                }],
            }
        }


class AdyenTerminal(models.Model):
    _name = 'adyen.terminal'
    _description = 'Adyen for Plaforms Terminal'
    _rec_name = 'terminal_uuid'

    adyen_account_id = fields.Many2one('adyen.account', ondelete='cascade')
    store_id = fields.Many2one('adyen.store')
    terminal_uuid = fields.Char('Terminal ID')

    @api.model
    def _sync_adyen_terminals(self):
        for adyen_store_id in self.env['adyen.store'].search([]):
            response = adyen_store_id.adyen_account_id._adyen_rpc('connected_terminals', {
                'store': adyen_store_id.store_uuid,
            })
            terminals_in_db = set(self.search([('store_id', '=', adyen_store_id.id)]).mapped('terminal_uuid'))

            # Added terminals
            for terminal in set(response.get('uniqueTerminalIds')) - terminals_in_db:
                self.sudo().create({
                    'adyen_account_id': adyen_store_id.adyen_account_id.id,
                    'store_id': adyen_store_id.id,
                    'terminal_uuid': terminal,
                })
