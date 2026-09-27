from markupsafe import Markup
from odoo import api, fields, models, _


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    @api.model
    def _default_report_footer(self):
        # Override to add the FR SIRET to the footer for French companies.
        siret = self.env.company.partner_id._get_additional_identifier('FR_SIRET') if self.env.company.country_code == 'FR' else None
        if not siret:
            return super()._default_report_footer()
        return super()._default_report_footer() + Markup('<br/>%s') % _('SIRET: %s', siret)

    report_footer = fields.Html(default=_default_report_footer)
