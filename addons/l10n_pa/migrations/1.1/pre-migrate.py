# Part of Odoo. See LICENSE file for full copyright and licensing details.


def migrate(cr, version):
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
