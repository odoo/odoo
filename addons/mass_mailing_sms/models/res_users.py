# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models, modules


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _get_activity_groups(self):
        """Override to split the single 'mailing.mailing' activity group.

        This method intercepts all mass_mailing activities and divides them
        into two distinct groups for the systray:
        - **Email Marketing**: mailings of type 'mail'.
        - **SMS Marketing**: mailings of type 'sms'.
        """
        groups = super()._get_activity_groups()

        mailing_group = next((g for g in groups if g['model'] == 'mailing.mailing'), None)
        if not mailing_group:
            return groups
        groups.remove(mailing_group)

        all_activities = self.env['mail.activity'].browse(mailing_group['activity_ids'])

        mailing_ids = all_activities.mapped('res_id')
        mailings = self.env['mailing.mailing'].browse(mailing_ids)
        type_map = {m.id: m.mailing_type for m in mailings}

        email_activities = all_activities.filtered(lambda a: type_map.get(a.res_id) == 'mail')
        sms_activities = all_activities.filtered(lambda a: type_map.get(a.res_id) == 'sms')

        # Format Email
        if email_activities:
            email_group = self._format_activity_group('mailing.mailing', email_activities)
            email_group.update({
                'name': _('Email Marketing'),
                'icon': modules.module.get_module_icon('mass_mailing'),
                'domain': [("active", "in", [True, False]), ("mailing_type", "=", 'mail')],
            })
            groups.append(email_group)

        # Format SMS
        if sms_activities:
            sms_group = self._format_activity_group('mailing.mailing', sms_activities)
            sms_group.update({
                'name': _('SMS Marketing'),
                'icon': modules.module.get_module_icon('mass_mailing_sms'),
                'domain': [("active", "in", [True, False]), ("mailing_type", "=", 'sms')],
            })
            groups.append(sms_group)

        return groups
