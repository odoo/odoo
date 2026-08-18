"""Post-install hooks for the ``invoice_agent`` module.

The deployment exposes the public base URL through the ``URL`` environment
variable (see docker-compose.yml). Odoo's runtime web URL is stored in the
``web.base.url`` system parameter, which Odoo otherwise auto-guesses from the
browser origin on the first admin login. Seeding it explicitly means every
generated link (reports, portals, email templates, API responses) uses the
canonical public URL from day one — including on upgrades.
"""

import logging
import os

_logger = logging.getLogger(__name__)


def _backfill_job_uuids(env):
    """Backfill ``invoice.agent.job.job_uuid`` on upgrade.

    v0.9 added ``job_uuid`` to the outbox row (UNIQUE) so a dead-letter can
    be correlated back to its row and redelivery is a no-op. Rows created
    before v0.9 carry no ``job_uuid``; the move's ``ai_job_uuid`` is the same
    correlation id the publisher already sends, so copy it over. Rows whose
    move has no uuid yet keep NULL — PostgreSQL UNIQUE tolerates multiple
    NULLs, and the drain backfills at publish time.
    """
    env.cr.execute(
        """
        UPDATE invoice_agent_job AS job
        SET job_uuid = move.ai_job_uuid
        FROM account_move AS move
        WHERE job.move_id = move.id
          AND (job.job_uuid IS NULL OR job.job_uuid = '')
          AND move.ai_job_uuid IS NOT NULL
          AND move.ai_job_uuid <> ''
        """
    )
    count = env.cr.rowcount
    if count:
        _logger.info("invoice_agent: backfilled job_uuid on %d outbox rows", count)


def post_init_hook(env):
    """Seed ``web.base.url`` and run the v0.9 outbox backfill.

    Deliberately runs on every install *and* module upgrade so that changing
    ``URL=`` in ``.env`` and releasing is enough to re-point the ERP, and so
    the idempotency columns are populated on existing deployments.

    Odoo invokes this hook with a single ``env`` argument (superuser
    environment loaded with the module's registry).
    """
    _backfill_job_uuids(env)

    base_url = os.environ.get("URL", "").strip()
    if not (base_url.startswith("http://") or base_url.startswith("https://")):
        _logger.warning(
            "invoice_agent: URL env is missing or not a valid base URL ('%s') — "
            "leaving web.base.url untouched. Set the URL variable in .env.",
            base_url,
        )
        return

    icp = env["ir.config_parameter"]
    icp.set_param("web.base.url", base_url)
    # Freeze it: unless 'web.base.url.freeze' is set, Odoo overwrites
    # web.base.url with the browser origin on every admin login.
    icp.set_param("web.base.url.freeze", "True")

    _logger.info("invoice_agent: web.base.url set to %s (frozen)", base_url)
