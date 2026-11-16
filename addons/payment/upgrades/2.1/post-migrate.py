from odoo import SUPERUSER_ID, api
from odoo.fields import Command


def migrate(cr, version):
    """
    Add the countries of the SEPA zone to the SEPA Direct Debit payment method.

    The payment method is `noupdate`: its supported countries are not refreshed by a module update.
    Countries are only added, never removed, to keep those added manually.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    sdd_method = env.ref('payment.payment_method_sepa_direct_debit', raise_if_not_found=False)
    sepa_zone = env.ref('base.sepa_zone', raise_if_not_found=False)
    if not sdd_method or not sepa_zone:
        return

    missing_countries = sepa_zone.country_ids - sdd_method.supported_country_ids
    if missing_countries:
        sdd_method.supported_country_ids = [Command.link(country.id) for country in missing_countries]
