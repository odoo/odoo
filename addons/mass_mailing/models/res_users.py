# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class Users(models.Model):
    _name = 'res.users'
    _inherit = ['res.users']

    @api.model
    def systray_get_activities(self):
        """ Update systray name of mailing.mailing from "Mass Mailing"
            to "Email Marketing".
        """
        activities = super(Users, self).systray_get_activities()
        for activity in activities:
            if activity.get('model') == 'mailing.mailing':
                activity['name'] = _('Email Marketing')
                break
        return activities

    def write(self, values):
        if values.get('email') and self == self.env.ref('base.user_admin'):
            contact_data = self.env.ref('mass_mailing.mass_mailing_contact_0', raise_if_not_found=False)
            if contact_data:
                contact_data.email = values['email']
        return super(Users, self).write(values)
