# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools.sql import column_exists


def migrate(cr, version):
    """ income_tax_id is now stored on res.partner, res.company only keeps a
    related field. Copy the values that were stored on the companies to their
    partners, then drop the obsolete column.
    """
    if not column_exists(cr, 'res_company', 'income_tax_id'):
        return

    cr.execute("""
        UPDATE res_partner p
           SET income_tax_id = c.income_tax_id
          FROM res_company c
         WHERE c.partner_id = p.id
           AND c.income_tax_id IS NOT NULL
           AND p.income_tax_id IS NULL
    """)
    cr.execute('ALTER TABLE res_company DROP COLUMN income_tax_id')
