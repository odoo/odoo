# Copyright 2020 VentorTech OU
# Part of Ventor modules. See LICENSE file for full copyright and licensing details.

def migrate(cr, version):
    cr.execute("DELETE FROM product_barcode_multi WHERE name IS NULL OR name = '' OR product_id IS NULL")
