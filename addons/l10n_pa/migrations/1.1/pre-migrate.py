# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tools.sql import column_exists, table_exists


def migrate(cr, version):
    # Some upgrade paths (e.g. crossing a major version) reach this script
    # before the table is (re)created, so there is nothing to renumber yet.
    if not table_exists(cr, 'l10n_pa_res_city_corregimiento') or \
            not column_exists(cr, 'l10n_pa_res_city_corregimiento', 'l10n_pa_code'):
        return

    # New districts were inserted in the official DGI division, so several
    # existing corregimientos are renumbered and some l10n_pa_code values
    # move from one record to another. Clearing the column to a per-row
    # placeholder first avoids a transient collision with the unique
    # constraint while data/l10n_pa.res.city.corregimiento.csv reassigns
    # each record to its new code.
    cr.execute("""
        UPDATE l10n_pa_res_city_corregimiento
        SET l10n_pa_code = 'tmp-' || id
    """)
