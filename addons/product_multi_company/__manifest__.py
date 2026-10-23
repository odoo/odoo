# Copyright 2015-2016 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

{
    "name": "Product multi-company",
    "summary": "Select individually the product template visibility on each " "company",
    "author": "Tecnativa," "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/multi-company",
    "category": "Product Management",
    "version": "16.0.1.0.2",
    "license": "AGPL-3",
    "depends": ["base_multi_company", "product"],
    "data": ["views/product_template_view.xml"],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
}
