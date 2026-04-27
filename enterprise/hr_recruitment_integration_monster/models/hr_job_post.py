# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class JobPost(models.Model):
    _inherit = 'hr.job.post'

    def _delete_post(self):
        self.ensure_one()
        if self.platform_id != self.env.ref(
            'hr_recruitment_integration_monster.hr_recruitment_platform_monster'
        ):
            return super()._delete_post()

        if not self.api_data:
            return self.write({
                'status': 'failure',
                'status_message': _('This Monster.com job post is not linked to an actual job post.'),
            })

        data = {
            'jobAction': 'delete',
            'jobRefCode': self.api_data['jobRefCode'],
        }
        response = self.platform_id._post_api_call(data)
        return self.write(response)
