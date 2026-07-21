from odoo.tools.sql import column_exists, create_column

from . import controllers
from . import models
from . import wizard
from . import tools


def _pre_init_pdp(env):
    if not column_exists(env.cr, "account_move", "pdp_ppf_move_state"):
        create_column(env.cr, "account_move", "pdp_ppf_move_state", "varchar")
        create_column(env.cr, "account_move", "pdp_ppf_lifecycle_state", "varchar")
        create_column(env.cr, "account_move", "pdp_lifecycle_residual", "numeric")
        create_column(env.cr, "account_peppol_response", "pdp_ppf_state", "varchar")
        create_column(env.cr, "account_move", "l10n_fr_pdp_last_flow_id", "int4")
        create_column(env.cr, "account_move", "l10n_fr_pdp_status", "varchar")
        create_column(env.cr, "account_move", "l10n_fr_pdp_flow_10_report_type", "varchar")
        create_column(env.cr, "account_move", "l10n_fr_pdp_flow_10_operation_type", "varchar")
        create_column(env.cr, "account_move", "l10n_fr_pdp_has_error", "bool")


def _post_init_pdp(env):
    """Update templates for Factur-X."""
    for view_name in [
        'account_edi_ubl_cii.account_invoice_partner_facturx_export_22',
        'account_edi_ubl_cii.account_invoice_facturx_export_22',
    ]:
        view = env.ref(view_name).sudo()
        view.reset_arch(mode="hard")

    demo_company_partner = env.ref('base.partner_demo_company_fr', raise_if_not_found=False)
    if demo_company_partner and demo_company_partner not in demo_company_partner._get_partners_to_skip_peppol_computation():
        demo_company_partner.peppol_eas = False
        demo_company_partner.peppol_endpoint = False
        demo_company_partner._compute_peppol_eas()
        demo_company_partner._compute_peppol_endpoint()


def uninstall_hook(env):
    env["res.partner"]._clear_removed_edi_formats("ubl_21_fr")
