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
        company = self.env.company
        address_format, company_data = company.partner_id._prepare_display_address()
        address_format = self._clean_address_format(address_format, company_data)
        # company_name may *still* be missing from prepared address in case commercial_company_name is falsy
        if 'company_name' not in address_format:
            address_format = '%(company_name)s\n' + address_format
            company_data['company_name'] = company_data['company_name'] or company.name
        if company.country_code == 'MA':
            address_format += '\nICE: %(ice)s\n'
            company_data['ice'] = company.ice
        return Markup(nl2br(address_format)) % company_data

    company_details = fields.Html(related='company_id.company_details', readonly=False, default=_default_company_details)
