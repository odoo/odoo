from . import models

def _create_demo_config_param(env):
    env['ir.config_parameter'].set_str('account_edi_proxy_client.demo', 'demo')
