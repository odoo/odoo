from . import models
from . import wizard


def _l10n_ae_ubl_pint_post_init_hook(env):
    for company in env['res.company'].search([('chart_template', '=', 'ae'), ('parent_id', '=', False)]):
        Template = env['account.chart.template'].with_company(company)
        tax_data = Template._get_ae_ubl_pint_account_tax()
        # Filter out data for non-existing taxes; else this function will raise.
        # In case of data for a non-existing tax we would try to create that tax.
        # This would fail because we don't supply enough information in this module (just `ubl_cii_tax_category_code`).
        tax_data = {
            xmlid: value
            for xmlid, value in tax_data.items()
            if Template.ref(xmlid, raise_if_not_found=False)
        }
        Template._load_data({
            'account.tax': tax_data,
        })


def uninstall_hook(env):
    env["res.partner"]._clear_removed_edi_formats("pint_ae")
