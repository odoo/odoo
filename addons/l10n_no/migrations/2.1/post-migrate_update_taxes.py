# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.models.chart_template import update_taxes_from_templates


def migrate(cr, version):
<<<<<<< HEAD:addons/l10n_no/migrations/2.1/post-migrate_update_taxes.py
    update_taxes_from_templates(cr, 'l10n_no.no_chart_template')
||||||| parent of 39472103027 (temp):addons/l10n_de_skr04/migrations/3.1/post-migrate_update_taxes.py
    update_taxes_from_templates(cr, 'l10n_de_skr04.l10n_de_chart_template')
=======
    update_taxes_from_templates(cr, 'l10n_de_skr04.l10n_chart_de_skr04')
>>>>>>> 39472103027 (temp):addons/l10n_de_skr04/migrations/3.1/post-migrate_update_taxes.py
