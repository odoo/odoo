from odoo import models, api


class MySubscription(models.AbstractModel):
    _name = 'mysubscription.mysubscription'
    _description = 'Subscription Dashboard Helper'

    @api.model
    def get_dashboard_data(self):
        is_system = self.env.is_system()
        icp_sudo = self.env['ir.config_parameter'].sudo()

        data = {
            'expiration_date': icp_sudo.get_str('database.expiration_date'),
            'expiration_reason': icp_sudo.get_str('database.expiration_reason'),
            'base_url': icp_sudo.get_str('web.base.url'),
            'is_system': is_system,
        }

        if is_system:
            data['enterprise_code'] = icp_sudo.get_str('database.enterprise_code')
        else:
            data['enterprise_code'] = None

        return data

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
