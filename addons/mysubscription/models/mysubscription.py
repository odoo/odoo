from odoo import models, api


class MySubscription(models.AbstractModel):
    _name = 'mysubscription.mysubscription'
    _description = 'Subscription Dashboard Helper'

    @api.model
    def get_dashboard_data(self):
        is_admin = self.env.is_admin()
        icp_sudo = self.env['ir.config_parameter'].sudo()

        data = {
            'expiration_date': icp_sudo.get_str('database.expiration_date'),
            'expiration_reason': icp_sudo.get_str('database.expiration_reason'),
            'base_url': icp_sudo.get_str('web.base.url'),
            'is_admin': is_admin,
        }

        if is_admin:
            data['enterprise_code'] = icp_sudo.get_str('database.enterprise_code')
        else:
            data['enterprise_code'] = '********'

        return data

    @api.model
    def get_iap_data(self):
        is_admin = self.env.is_admin()
        if not is_admin:
            return []

        iap_sudo = self.env['iap.account'].sudo()
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
