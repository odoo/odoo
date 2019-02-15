# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Survey(models.Model):
    _inherit = 'survey.survey'

    def _check_answer_creation(self, user, partner, email, test_entry=False, check_attempts=True, invite_token=False):
        """ Overridden to allow website_publisher to test certifications. """
        self.ensure_one()
        if test_entry and user.has_group('website.group_website_publisher'):
            return True

        return super(Survey, self)._check_answer_creation(user, partner, email, test_entry=test_entry, check_attempts=check_attempts, invite_token=invite_token)
