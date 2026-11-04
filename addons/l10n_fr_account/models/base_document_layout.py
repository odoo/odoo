from markupsafe import Markup
from odoo import api, models, _


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    @api.model
    def _default_report_footer_content(self):
        # Override to add the FR SIRET to the footer for French companies.
        siret = self.env.company.partner_id._get_additional_identifier('FR_SIRET') if self.env.company.country_code == 'FR' else None
        if not siret:
            return super()._default_report_footer_content()
        return super()._default_report_footer_content() + Markup('<br/>%s') % _('SIRET: %s', siret)
