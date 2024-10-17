from . import models

from .models.account_edi_proxy_user import Account_Edi_Proxy_ClientUser
from .models.key import CertificateKey
from .models.res_company import ResCompany

def _create_demo_config_param(env):
    env['ir.config_parameter'].set_param('account_edi_proxy_client.demo', 'demo')
