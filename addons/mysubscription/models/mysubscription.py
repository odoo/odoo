from datetime import datetime

from odoo import models, api, fields


class MySubscription(models.AbstractModel):
    _name = 'mysubscription.mysubscription'
    _description = 'Subscription Dashboard Helper'

    @api.model
    def get_dashboard_data(self):
        is_system = self.env.is_system()
        icp_sudo = self.env['ir.config_parameter'].sudo()

        enterprise_code = icp_sudo.get_str('database.enterprise_code')
        expiration_date = icp_sudo.get_str('database.expiration_date')

        return {
            'base_url': icp_sudo.get_str('web.base.url'),
            'has_subscription': self._has_subscription(enterprise_code, expiration_date),
            'enterprise_code': enterprise_code if is_system else '',
        }

    def _has_subscription(self, enterprise_code, expiration_date):
        """ We need both an enterprise_code and a future expiration_date to
        consider the database as having an active subscription. """
        if not enterprise_code or not expiration_date:
            return False
        expiration_datetime = fields.Datetime.from_string(expiration_date)
        return bool(expiration_datetime) and expiration_datetime > datetime.utcnow()

    @api.model
    def get_iap_data(self):
        is_system = self.env.is_system()
        if not is_system or 'iap.account' not in self.env:
            return []

        iap_sudo = self.env['iap.account'].sudo()  # noqa: OLS03001
        accounts = iap_sudo.search([])

        data = []
        for account in accounts:
            data.append({
                'name': account.name or account.service_name,
                'credit_url': iap_sudo.get_credits_url(
                    service_name=account.service_name,
                    account_token=account.account_token
                ),
                'balance': account.balance,
                'service_name': account.service_name,
                'action': account.action_open_iap_account(),
                'description': account.description,
            })
        return data
