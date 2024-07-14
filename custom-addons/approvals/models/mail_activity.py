# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def activity_format(self):
        result = super(MailActivity, self).activity_format()
        activity_type_approval_id = self.env.ref('approvals.mail_activity_data_approval').id
        for activity in result:
            if activity['activity_type_id'] and activity['activity_type_id'][0] == activity_type_approval_id and \
                    activity['res_model'] == 'approval.request':
                request = self.env['approval.request'].browse(activity['res_id'])
                approver = request.approver_ids.filtered(lambda approver: activity['user_id'][0] == approver.user_id.id)
                activity['approver_id'] = approver.id
                activity['approver_status'] = approver.status
        return result
