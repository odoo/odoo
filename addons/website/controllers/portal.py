# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request


class WebsiteCustomerPortal(CustomerPortal):

    def _document_check_access(self, model_name, document_id, access_token=None):
        document_sudo = super()._document_check_access(model_name, document_id, access_token=access_token)
        # Render a company-owned portal document on its own company's website,
        # whatever the host that served the request. If that company has no
        # website, drop the website from the context so the page falls back to
        # the plain portal, exactly as if the website module were not installed,
        # instead of being embedded in an unrelated company's website.
        if hasattr(document_sudo, '_get_portal_website'):
            website = document_sudo._get_portal_website().sudo()
            if website:
                # The request was authenticated for the host website's public
                # user (see IrHttp._auth_method_public()). When the document
                # lives on another website, realign the environment to that
                # website so its chrome renders consistently, mirroring the
                # frontend dispatch: switch a public visitor to the target
                # website's public user and pin its company.
                if request.env.user._is_public():
                    # website.user_id always represents the public user
                    request.update_env(user=website.user_id.id)
                    request.update_context(allowed_company_ids=website.company_id.ids)
                request.update_context(website_id=website.id)
            else:
                request.update_context(website_id=None)
        return document_sudo.with_env(request.env(su=True))
