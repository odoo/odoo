# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models


def post_init_hook(env):
    if registering_cron := env.ref('account_peppol.ir_cron_peppol_auto_register_services', raise_if_not_found=False):
        registering_cron._trigger()


def uninstall_hook(env):
    env["res.partner"]._clear_removed_edi_formats("pint_sg")
    env['account_edi_proxy_client.user']._peppol_auto_deregister_services('l10n_sg_ubl_pint')
