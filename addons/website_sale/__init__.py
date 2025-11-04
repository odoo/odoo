# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tools.sql import SQL

from . import controllers, models, report


def _post_init_hook(env):  # noqa: RUF067
    terms_conditions = env["ir.config_parameter"].get_bool("account.use_invoice_terms")
    if not terms_conditions:
        env["ir.config_parameter"].set_bool("account.use_invoice_terms", True)
    companies = env["res.company"].search([])
    for company in companies:
        company.terms_type = "html"
    env["website"].search([]).auth_signup_uninvited = "b2c"

    existing_websites = env["website"].search([])
    for website in existing_websites:
        website._create_checkout_steps()

    # suggest_optional_products is TRUE only if there are no optional products set
    env.execute_query(
        SQL(
            """
            UPDATE product_template
               SET suggest_optional_products = TRUE
             WHERE NOT EXISTS (
                 SELECT 1
                   FROM product_optional_rel r
                  WHERE r.src_id = product_template.id
                 )
               AND sale_ok IS TRUE
               AND is_published IS TRUE
            """
        )
    )


def uninstall_hook(env):  # noqa: RUF067
    """Need to reenable the `product` pricelist multi-company rule that were
    disabled to be 'overridden' for multi-website purpose.
    """
    pl_rule = env.ref("product.product_pricelist_comp_rule", raise_if_not_found=False)
    pl_item_rule = env.ref("product.product_pricelist_item_comp_rule", raise_if_not_found=False)
    multi_company_rules = pl_rule or env["ir.rule"]
    multi_company_rules += pl_item_rule or env["ir.rule"]
    multi_company_rules.write({"active": True})
