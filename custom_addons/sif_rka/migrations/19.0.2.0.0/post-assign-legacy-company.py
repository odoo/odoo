import logging

from odoo import SUPERUSER_ID, api


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    main_company = env.ref("base.main_company")
    cr.execute(
        "UPDATE sif_rka_budget SET company_id = %s WHERE company_id IS NULL",
        (main_company.id,),
    )
    budgets_updated = cr.rowcount
    cr.execute(
        """
        UPDATE sif_rka_budget_month AS month
           SET company_id = rka.company_id
          FROM sif_rka_budget AS rka
         WHERE month.rka_id = rka.id
           AND month.company_id IS DISTINCT FROM rka.company_id
        """
    )
    _logger.info(
        "Assigned %s legacy RKA budgets without a company to %s; branch budgets will be created separately.",
        budgets_updated,
        main_company.display_name,
    )
