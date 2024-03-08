from odoo.addons.account.models.chart_template import update_taxes_from_templates

def migrate(cr, version):
    # Change tax tag ve38 from tax repartition lines to base repartition lines
    update_taxes_from_templates(cr, 'l10n_it.l10n_it_chart_template_generic')
