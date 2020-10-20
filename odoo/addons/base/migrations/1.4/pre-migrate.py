def migrate(cr, version):
    """Drop wrong index. Lets Odoo recreate it later."""
    cr.execute("DROP INDEX IF EXISTS res_partner_vat_index")
