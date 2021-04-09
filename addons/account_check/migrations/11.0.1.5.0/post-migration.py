from openupgradelib import openupgrade
import logging

_logger = logging.getLogger(__name__)


@openupgrade.migrate()
def migrate(env, version):

    _logger.info('Setting inital values for amount_company_currency')
    env.cr.execute("""
    UPDATE account_check AS ac SET amount_company_currency = ac.amount
    FROM res_company AS rc
    WHERE rc.id = ac.company_id and ac.currency_id = rc.currency_id
    """)
