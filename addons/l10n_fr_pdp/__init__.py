from . import models
from . import wizard
from . import tools


def _post_init_pdp(env):
    """Update templates for Factur-X."""
    for view_name in [
        'account_edi_ubl_cii.account_invoice_partner_facturx_export_22',
        'account_edi_ubl_cii.account_invoice_facturx_export_22',
    ]:
        view = env.ref(view_name).sudo()
        view.reset_arch(mode="hard")


def uninstall_hook(env):
    env["res.partner"]._clear_removed_edi_formats("ubl_21_fr")
