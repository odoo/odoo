# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class Users(models.Model):
    _name = 'res.users'
    _inherit = ['res.users']

    @api.model
    def _get_systray_group_custom_infos(self):
        """ Update systray name of mailing.mailing from "Mass Mailing"
            to "Email Marketing"/"SMS Marketing".
        """
        result = super()._get_systray_group_custom_infos()
        result['mass_mailing_sms'] = {
            'name': _('SMS Marketing'),
            'domain': [['mailing_type', '=', 'sms']],
        }
        result['mass_mailing'] = {
            'name': _('Email Marketing'),
            'domain': [['mailing_type', '!=', 'sms']],
        }
        return result

