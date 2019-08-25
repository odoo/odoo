# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailingList(models.Model):
    _inherit = 'mailing.list'

    def _compute_contact_nbr(self):
        if self.env.context.get('mailing_sms'):
            self.env.cr.execute('''
select list_id, count(*)
from mailing_contact_list_rel r
left join mailing_contact c on (r.contact_id=c.id)
left join phone_blacklist bl on c.phone_sanitized = bl.number and bl.active
where
    list_id in %s
    AND COALESCE(r.opt_out,FALSE) = FALSE
    AND c.phone_sanitized IS NOT NULL
    AND bl.id IS NULL
group by list_id''', (tuple(self.ids), ))
            data = dict(self.env.cr.fetchall())
            for mailing_list in self:
                mailing_list.contact_nbr = data.get(mailing_list.id, 0)
            return
        return super(MailingList, self)._compute_contact_nbr()

    def action_view_contacts(self):
        if self.env.context.get('mailing_sms'):
            action = self.env.ref('mass_mailing_sms.mailing_contact_action_sms').read()[0]
            action['domain'] = [('list_ids', 'in', self.ids)]
            context = dict(self.env.context, search_default_filter_valid_sms_recipient=1, default_list_ids=self.ids)
            action['context'] = context
            return action
        return super(MailingList, self).action_view_contacts()
