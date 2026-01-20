from . import models


def _l10n_sg_purchase_peppol_post_init(env):
    registering_cron = env.ref('account_peppol.ir_cron_peppol_auto_register_services')
    registering_cron._trigger()


def _l10n_sg_purchase_peppol_uninstall(env):
    env['account_edi_proxy_client.user']._peppol_auto_deregister_services('l10n_sg_purchase_peppol')
