from odoo.tools.sql import column_exists, create_column, table_exists

from . import models
from . import wizard


def _l10n_ae_ubl_pint_pre_init_hook(env):
    """ Force the creation of the columns and tables to avoid having the ORM compute on potentially millions of records. """
    if not column_exists(env.cr, 'account_move', 'l10n_ae_invoice_type'):
        create_column(env.cr, 'account_move', 'l10n_ae_invoice_type', 'varchar')
        create_column(env.cr, 'account_move_line', 'l10n_ae_item_type', 'varchar')
        create_column(env.cr, 'account_move_line', 'l10n_ae_goods_service_type', 'varchar')
        create_column(env.cr, 'account_move_line', 'l10n_ae_hs_code', 'varchar')
        create_column(env.cr, 'account_move_line', 'l10n_ae_service_accounting_code', 'varchar')

    if not table_exists(env.cr, 'account_move_l10n_ae_transaction_type_rel'):
        env.cr.execute("""
            CREATE TABLE account_move_l10n_ae_transaction_type_rel (
                account_move_id INTEGER NOT NULL,
                l10n_ae_transaction_type_id INTEGER NOT NULL,
                PRIMARY KEY (account_move_id, l10n_ae_transaction_type_id)
            );
            COMMENT ON TABLE account_move_l10n_ae_transaction_type_rel IS 'RELATION BETWEEN account_move AND l10n_ae_transaction_type';
            CREATE INDEX ON account_move_l10n_ae_transaction_type_rel (l10n_ae_transaction_type_id, account_move_id);
        """)


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
