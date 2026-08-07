# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Domain
from odoo.tools.sql import SQL

from . import controllers, models, report


def setup_website_tax_display(env, tax_display, country_code):
    """Ensure websites in the specified country use the given default tax display.

    Used by localization modules who override the default behavior.
    """
    env["website"].search(
        Domain([
            ("show_line_subtotals_tax_selection", "!=", tax_display),
            ("company_id.account_fiscal_country_id.code", "=", country_code),
        ])
    ).show_line_subtotals_tax_selection = tax_display


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

    recovery_template = env.ref(
        "website_sale.mail_template_sale_cart_recovery", raise_if_not_found=False
    )
    if recovery_template:
        existing_websites.cart_recovery_mail_template_id = recovery_template


def uninstall_hook(env):
    """Need to reenable the `product` pricelist multi-company rule that were
    disabled to be 'overridden' for multi-website purpose.
    """
    if access := env.ref("product.product_pricelist_comp_rule", raise_if_not_found=False):
        access.active = True
    if access := env.ref("product.product_pricelist_item_comp_rule", raise_if_not_found=False):
        access.active = True
