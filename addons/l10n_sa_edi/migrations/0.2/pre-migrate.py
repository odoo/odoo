from odoo.tools.sql import column_exists, rename_column


def migrate(cr, version):
    if column_exists(cr, "account_journal", "l10n_sa_serial_number"):
        rename_column(cr, "account_journal", "l10n_sa_serial_number", "l10n_sa_edi_serial_number")
