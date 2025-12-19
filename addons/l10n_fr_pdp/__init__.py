from odoo.tools.sql import column_exists, create_column

from . import controllers
from . import models
from . import wizard
from . import tools


def _pre_init_pdp(env):
    """
        Force the creation of the columns to avoid having the ORM compute on potentially millions of records.
        Mimic the compute method of pdp_identifier fill the column.
    """
    if not column_exists(env.cr, "account_move", "pdp_move_state"):
        create_column(env.cr, "account_move", "pdp_move_state", "varchar")
        create_column(env.cr, "res_partner", "pdp_identifier", "varchar")

    # TODO: check when pdp identifier computation is done
    query = """
        WITH _fr AS (
            SELECT p.id
              FROM res_partner p
         LEFT JOIN res_country c
                ON c.id = p.country_id
             WHERE p.vat ILIKE 'FR%'
                OR c.code = 'FR'
        )
        UPDATE res_partner p
           SET pdp_identifier = p.siret
          FROM _fr
         WHERE _fr.id = p.id
    """
    env.cr.execute(query)


def uninstall_hook(env):
    env["res.partner"]._clear_removed_edi_formats("ubl_21_fr")
