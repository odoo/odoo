from odoo.modules.neutralize import get_installed_modules, get_neutralization_queries
from odoo.tests import TransactionCase, tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAccountEdiProxyNeutralize(TransactionCase):

    def test_all_proxy_types_go_offline_after_neutralize(self):
        """Every proxy user must be archived or in 'demo' mode after neutralization"""
        proxy_types = self.env['account_edi_proxy_client.user']._fields['proxy_type'].get_values(self.env)

        key = self.env['certificate.key']._generate_rsa_private_key(self.env.company, name='neutralize_test')
        users = self.env['account_edi_proxy_client.user']
        for proxy_type in proxy_types:
            # one company per proxy type
            users |= self.env['account_edi_proxy_client.user'].create({
                'id_client': f'client_{proxy_type}',
                'company_id': self.env['res.company'].create({'name': proxy_type}).id,
                'edi_identification': proxy_type,
                'private_key_id': key.id,
                'proxy_type': proxy_type,
                'edi_mode': 'prod',
            })

        # Only run the neutralization scripts that touch proxy users
        for query in get_neutralization_queries(get_installed_modules(self.env.cr)):
            if users._table in query:
                self.env.cr.execute(query)
        users.invalidate_recordset(['edi_mode', 'active'])

        # l10n_au_hr_payroll_api neutralizes by deleting the proxy user, hence the exists()
        still_live = users.exists().filtered(lambda u: u.active and u.edi_mode != 'demo').mapped('proxy_type')
        self.assertFalse(still_live, f"proxy_type(s) still reachable after neutralization: {still_live}")
