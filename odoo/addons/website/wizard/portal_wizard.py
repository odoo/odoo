# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PortalWizardUser(models.TransientModel):
    _inherit = ['portal.wizard.user']

    def _get_similar_users_domain(self, portal_users_with_email):
        """ Returns the domain needed to find the users that have the same email
        as portal users depending on their linked website characteristics.
        :param portal_users_with_email: portal users that have an email address.
        """
        similar_user_domain = super()._get_similar_users_domain(portal_users_with_email)
        portal_user_website_ids = []
        for portal_user in portal_users_with_email:
            portal_user_website_id = portal_user.partner_id.website_id.id
            if portal_user_website_id and portal_user_website_id not in portal_user_website_ids:
                # If a portal user is linked to a website, search for the users
                # that are linked to the same website.
                portal_user_website_ids.append(portal_user_website_id)
            elif not portal_user_website_id and False not in portal_user_website_ids:
                # If a portal user is not linked to a website, search for the
                # users that are not linked to a website and the users that are
                # linked to the current website.
                portal_user_website_ids.extend([False, self.env['website'].get_current_website().id])
        similar_user_domain.append(('website_id', 'in', portal_user_website_ids))
        return similar_user_domain

    def _get_similar_users_fields(self):
        """ Returns a list of field elements to extract from users.
        """
        similar_user_fields = super()._get_similar_users_fields()
        similar_user_fields.append('website_id')
        return similar_user_fields

    def _is_portal_similar_than_user(self, user, portal_user):
        """ Checks if the credentials of a portal user and a user are the same
        (users are distinct, their emails are similar and their linked websites
        are incompatible).
        """
        if super()._is_portal_similar_than_user(user, portal_user):
            if portal_user.partner_id.website_id:
                # If the partner is linked to a website, it is considered as
                # 'already registered' if the user is linked to the same
                # website.
                return user['website_id'] and user['website_id'][0] == portal_user.partner_id.website_id.id
            # If the partner is not linked to a website, it means it has access
            # to all the websites; the partner is considered as 'already
            # registered' if the user is not linked to a website or if the user
            # is linked to the current website as the current partner will be
            # redirected to the current website when it will create its account.
            return not user['website_id'] or user['website_id'][0] == self.env['website'].get_current_website().id
        return False
