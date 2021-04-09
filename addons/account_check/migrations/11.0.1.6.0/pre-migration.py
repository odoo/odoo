from openupgradelib import openupgrade
import logging

_logger = logging.getLogger(__name__)


@openupgrade.migrate()
def migrate(env, version):

    _logger.info('Setting inital values for currency_id')
    env.cr.execute("""
    UPDATE account_check AS ac SET currency_id = rc.currency_id
    FROM res_company AS rc
    WHERE rc.id = ac.company_id and ac.currency_id is null
    """)
