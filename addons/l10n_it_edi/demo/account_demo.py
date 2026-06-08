from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template(template='it', model='res.partner', demo=True)
    def _l10n_it_edi_get_partner_demo_data(self):
        return {
            'res_partner_it_b2b': {
                'l10n_it_codice_fiscale': '01234560157',
                'l10n_it_pa_index': 'M5UXCR1',
            },
            'res_partner_it_pa': {
                'l10n_it_codice_fiscale': '01199250158',
                'l10n_it_pa_index': 'UFJ9DC',
            },
            'res_partner_it_b2c': {
                'l10n_it_codice_fiscale': 'RSSMRA80A01F205X',
            },
        }
