from . import models
from . import wizard


def _account_peppol_response_post_init(env):
    registering_cron = env.ref('account_peppol_response.ir_cron_peppol_auto_register_services')
    registering_cron._trigger()


def _account_peppol_response_uninstall(env):
    env['account_edi_proxy_client.user']._peppol_auto_deregister_services('account_peppol_response')
