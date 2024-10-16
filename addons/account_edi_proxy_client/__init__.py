from .models import Account_Edi_Proxy_ClientUser, CertificateKey, ResCompany

def _create_demo_config_param(env):
    env['ir.config_parameter'].set_param('account_edi_proxy_client.demo', 'demo')
