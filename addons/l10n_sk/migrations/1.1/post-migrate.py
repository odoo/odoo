# Part of Odoo. See LICENSE file for full copyright and licensing details.


def migrate(cr, version):
    """ income_tax_id is now stored on res.partner, res.company only keeps a
    related field. Copy the values that were stored on the companies to their
    partners.
    """
    cr.execute("""
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'res_company'
           AND column_name = 'income_tax_id'
    """)
    if not cr.fetchone():
        return

    cr.execute("""
        UPDATE res_partner p
           SET income_tax_id = c.income_tax_id
          FROM res_company c
         WHERE c.partner_id = p.id
           AND c.income_tax_id IS NOT NULL
           AND p.income_tax_id IS NULL
    """)
