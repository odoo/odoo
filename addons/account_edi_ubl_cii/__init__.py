from odoo.tools.safe_eval import safe_whitelist

from . import models
from . import wizard


def uninstall_hook(env):
    env["res.partner"]._clear_removed_edi_formats(
        "facturx",
        "nlcius",
        "ubl_a_nz",
        "ubl_bis3",
        "ubl_sg",
        "xrechnung",
    )


safe_whitelist.add_function('odoo.addons.account_edi_ubl_cii.models.account_edi_xml_cii_facturx.AccountEdiXmlCii._export_invoice_vals.<locals>.*')
