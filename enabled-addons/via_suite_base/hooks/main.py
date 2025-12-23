import logging

from .currencies import ensure_currencies
from .company import ensure_company_currency_usd
from .oauth_keycloak import configure_keycloak_oauth_provider
from .users_groups import ensure_default_admin_users_are_admins
from .mail_ses import configure_amazon_ses_outgoing_mail
from .users_seed import ensure_default_admin_users_exist

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    _logger.info("Running via_suite_base post_init_hook...")

    ensure_currencies(env)
    ensure_company_currency_usd(env)
    configure_keycloak_oauth_provider(env)

    configure_amazon_ses_outgoing_mail(env)

    ensure_default_admin_users_exist(env)
    ensure_default_admin_users_are_admins(env)

    _logger.info("via_suite_base post_init_hook completed.")