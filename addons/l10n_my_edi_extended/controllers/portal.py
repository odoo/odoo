# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.controllers.portal import PortalAccount
from odoo.http import request, route


class PortalAccountMy(PortalAccount):

    @route(['/my/account'], type='http', auth='user', website=True)
    def account(self, redirect=None, **post):
        # EXTENDS 'portal' to update the classification properly by casting it in advance
        if post and request.httprequest.method == 'POST':
            if 'l10n_my_edi_industrial_classification' in post:
                try:
                    post['l10n_my_edi_industrial_classification'] = int(post['l10n_my_edi_industrial_classification'])
                except (ValueError, TypeError, OverflowError):
                    post['l10n_my_edi_industrial_classification'] = False
        return super().account(redirect, **post)

    def _get_optional_fields(self):
        # EXTENDS 'portal'
        optional_fields = super()._get_optional_fields()
        optional_fields.extend(('l10n_my_identification_type', 'l10n_my_identification_number', 'l10n_my_edi_industrial_classification'))
        return optional_fields

    def _prepare_portal_layout_values(self):
        # EXTENDS 'portal'
        portal_layout_values = super()._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        portal_layout_values.update({
            'l10n_my_identification_types': dict(partner._fields['l10n_my_identification_type'].selection),
            'l10n_my_edi_industrial_classifications': request.env['l10n_my_edi.industry_classification'].sudo().search([]),
        })
        return portal_layout_values
