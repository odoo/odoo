# Part of Odoo. See LICENSE file for full copyright and licensing details


def migrate(cr, version):

    # account_move
    cr.execute("""
        ALTER TABLE account_move
        ADD COLUMN IF NOT EXISTS l10n_id_ebupot_document VARCHAR;
    """)
    cr.execute("""
        UPDATE account_move
        SET l10n_id_ebupot_document = 'CommercialInvoice'
        WHERE l10n_id_ebupot_document IS NULL;
    """)

    # account_payment
    cr.execute("""
        ALTER TABLE account_payment
        ADD COLUMN IF NOT EXISTS l10n_id_ebupot_doctype VARCHAR;
    """)
    cr.execute("""
        UPDATE account_payment
        SET l10n_id_ebupot_doctype = 'N/A'
        WHERE l10n_id_ebupot_doctype IS NULL;
    """)
