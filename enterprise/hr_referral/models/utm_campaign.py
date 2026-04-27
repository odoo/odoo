# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models

from odoo.exceptions import UserError


class UtmCampaign(models.Model):
    _inherit = 'utm.campaign'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_jobs(self):
        """ Already handled by ondelete='restrict', but let's show a nice error message """
        linked_jobs = self.env['hr.job'].sudo().search([
            ('utm_campaign_id', 'in', self.ids)
        ])

        if linked_jobs:
            raise UserError(_(
                "You cannot delete these UTM Campaigns as they are linked to the following jobs in "
                "Referral:\n%(job_names)s",
                job_names=', '.join(['"%s"' % name for name in linked_jobs.mapped('name')])))
