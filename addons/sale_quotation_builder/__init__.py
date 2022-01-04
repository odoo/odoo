# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models

def _pre_init_sale_quotation_builder(cr):
    """ Allow installing sale_quotation_builder in databases
    with large sale.order / sale.order.line tables.

    Since website_description fields computation is based
    on new fields added by the module, they will be empty anyway.

    By avoiding the computation of those fields,
    we reduce the installation time noticeably
    """
    cr.execute("""
        ALTER TABLE "sale_order"
        ADD COLUMN "website_description" text
    """)
    cr.execute("""
        ALTER TABLE "sale_order_line"
        ADD COLUMN "website_description" text
    """)
    cr.execute("""
        ALTER TABLE "sale_order_template_line"
        ADD COLUMN "website_description" text
    """)
    cr.execute("""
        ALTER TABLE "sale_order_template_option"
        ADD COLUMN "website_description" text
    """)
