from markupsafe import Markup
from odoo import api, models, _


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    @api.model
    def _default_report_footer(self):
        # Override to add the company.registry for FR companies
        if not (self.env.company.company_registry and self.env.company.country_code == 'FR'):
            return super()._default_report_footer()
        return super()._default_report_footer() + Markup('<br/>%s') % _('SIRET: %s', self.env.company.company_registry)
