# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.addons import web_tour, mail, contacts, digest


class ResUsers(contacts.ResUsers, mail.ResUsers, web_tour.ResUsers, digest.ResUsers):

    @api.model
    def _get_activity_groups(self):
        """ Update systray name of mailing.mailing from "Mass Mailing"
            to "Email Marketing".
        """
        activities = super()._get_activity_groups()
        for activity in activities:
            if activity.get('model') == 'mailing.mailing':
                activity['name'] = _('Email Marketing')
                break
        return activities
