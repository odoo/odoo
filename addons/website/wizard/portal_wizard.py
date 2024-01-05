# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools.translate import _


class PortalWizardUser(models.TransientModel):
    _inherit = ['portal.wizard.user']

    def _get_similar_user_domain(self, email):
        """ Returns the domain needed to find the users that have the same email
        as the current partner depending on its linked website characteristics.
        :param string email: the email of the current partner
        """
        similar_user_domain = super()._get_similar_user_domain(email)
        if self.partner_id.website_id:
            # If the partner is linked to a website, only keep the users that
            # are linked to this website.
            similar_user_domain.append(('website_id', '=', self.partner_id.website_id.id))
        else:
            # If the partner is not linked to a website, it means it has access
            # to all the websites; only keep the users that are not linked to a
            # website or the users that are linked to the current website as the
            # current partner will be redirected to the current website when it
            # will create its account.
            similar_user_domain.append(('website_id', 'in', [False, self.env['website'].get_current_website().id]))
        return similar_user_domain

    def _get_same_email_error_message(self, user_name):
        """ Returns the error message in case the current partner and an
        existing user have the same email and are linked to the same website.
        :param user_name: the user that has the same email and is linked to the
        same website as the current partner
        """
        return _('The contact "%s" has the same email as an existing user (%s) and has access to the same website.', self.partner_id.name, user_name)
