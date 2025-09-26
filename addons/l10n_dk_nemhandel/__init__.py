from odoo.tools.sql import column_exists, create_column

from . import models
from . import tools
from . import wizard


def _pre_init_nemhandel(env):
    """
        Force the creation of the columns to avoid having the ORM compute on potentially millions of records.
        Mimic the compute method of nemhandel_identifier_type and nemhandel_identifier_value to fill these columns.
    """
    if not column_exists(env.cr, "account_move", "nemhandel_move_state"):
        create_column(env.cr, "account_move", "nemhandel_move_state", "varchar")
        create_column(env.cr, "res_partner", "nemhandel_identifier_type", "varchar")
        create_column(env.cr, "res_partner", "nemhandel_identifier_value", "varchar")

    query = """
        WITH _dk AS (
            SELECT p.id
              FROM res_partner p
         LEFT JOIN res_country c
                ON c.id = p.country_id
             WHERE p.vat ILIKE 'DK%'
                OR c.code = 'DK'
        )
        UPDATE res_partner p
           SET nemhandel_identifier_type = '0184',
               nemhandel_identifier_value = p.company_registry
          FROM _dk
         WHERE _dk.id = p.id
    """
    env.cr.execute(query)
