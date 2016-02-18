# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from challenge import MAX_VISIBILITY_RANKING

class ResUsersGamificationGroup(models.Model):
    """ Update of res.users class
        - if adding groups to an user, check gamification.challenge linked to
        this group, and the user. This is done by overriding the write method.
    """
    _name = 'res.users'
    _inherit = ['res.users']

    def get_serialised_gamification_summary(self, excluded_categories=None):
        # Calling with explicit `browse` instead of `self.env.user` as the latter is a sudo `browse_record`
        return self.browse(self.env.uid)._serialised_goals_summary(excluded_categories=excluded_categories)

    def _serialised_goals_summary(self, excluded_categories=None):
        """Return a serialised list of goals assigned to the user, grouped by challenge
        :excluded_categories: list of challenge categories to exclude in search

        [
            {
                'id': <gamification.challenge id>,
                'name': <gamification.challenge name>,
                'visibility_mode': <visibility {ranking,personal}>,
                'currency': <res.currency id>,
                'lines': [(see gamification_challenge._get_serialized_challenge_lines() format)]
            },
        ]
        """
        all_goals_info = []
        domain = [('user_ids', 'in', self.env.uid), ('state', '=', 'inprogress')]
        if excluded_categories and isinstance(excluded_categories, list):
            domain.append(('category', 'not in', excluded_categories))
        for challenge in self.env['gamification.challenge'].search(domain):
            # serialize goals info to be able to use it in javascript
            lines = challenge._get_serialized_challenge_lines(self.id, restrict_top=MAX_VISIBILITY_RANKING)
            if lines:
                all_goals_info.append({
                    'id': challenge.id,
                    'name': challenge.name,
                    'visibility_mode': challenge.visibility_mode,
                    'currency': self.env.user.company_id.currency_id.id,
                    'lines': lines,
                })

        return all_goals_info

    def get_challenge_suggestions(self):
        """Return the list of challenges suggested to the user"""
        challenge_info = []
        for challenge in self.env['gamification.challenge'].search([('invited_user_ids', 'in', self.env.uid), ('state', '=', 'inprogress')]):
            values = {
                'id': challenge.id,
                'name': challenge.name,
                'description': challenge.description,
            }
            challenge_info.append(values)
        return challenge_info
