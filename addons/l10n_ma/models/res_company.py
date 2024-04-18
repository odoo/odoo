# Part of Odoo. See LICENSE file for full copyright and licensing details.
from markupsafe import Markup

from odoo import api, fields, models

from odoo.addons.base.models.ir_qweb_fields import nl2br


class ResCompany(models.Model):
    _inherit = 'res.company'

    ice = fields.Char("ICE", help='Common Company Identifier', default='')

class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    @api.model
    def _default_company_details(self):
        company_details = super()._default_company_details()
        if self.env.company.country_code == 'MA':
            company_details += Markup(nl2br(f"\nICE: {self.env.company.ice}\n"))
        return company_details

    company_details = fields.Html(related='company_id.company_details', readonly=False, default=_default_company_details)
