# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.l10n_ar.controllers.portal import L10nARCustomerPortal
from odoo.http import request


class L10nARWebsiteCustomerPortal(L10nARCustomerPortal):

    # TODO this is required because there is abug on odoo when consulting request.env.company return the main company
    # not actually the current company where the user is logged, after this is fix remove this method, meanwhile is
    # needed because let us to proper compute the AFIP Responsibility/ Identification Types for Argentinian company.
    def is_argentinian_company(self):
        if request.website:
            return request.website.sudo().company_id.country_id == request.env.ref('base.ar')
        return super().is_argentinian_company()
