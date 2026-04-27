# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields, models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EventMailScheduler(models.Model):
    _inherit = 'event.mail'

    notification_type = fields.Selection(selection_add=[('social_post', 'Social Post')])
    template_ref = fields.Reference(ondelete={'social.post.template': 'cascade'}, selection_add=[('social.post.template', 'Social Post')])

    @api.constrains('template_ref', 'interval_type')
    def _check_interval_type(self):
        """Cannot select "after_sub" if the notification type is "social_post"."""
        for mail in self:
            if mail.notification_type == 'social_post' and mail.interval_type == 'after_sub':
                raise UserError(_('As social posts have no recipients, they cannot be triggered by registrations.'))

    def _compute_notification_type(self):
        super()._compute_notification_type()
        social_schedulers = self.filtered(lambda scheduler: scheduler.template_ref and scheduler.template_ref._name == 'social.post.template')
        social_schedulers.notification_type = 'social_post'

    def _execute_event_based(self):
        social_schedulers = self.filtered(lambda scheduler: scheduler.notification_type == 'social_post')

        if social_schedulers:
            self.env['social.post'].sudo().create([
                scheduler.template_ref._prepare_social_post_values()
                for scheduler in social_schedulers
            ])._action_post()

            for scheduler in social_schedulers:
                scheduler.update({
                    'mail_done': True,
                    'mail_count_done': len(scheduler.template_ref.account_ids),
                })
        # do not call super for social schedulers as they have their own
        # computation for mail_done / mail_count_done; also avoid singleton errors
        remaining = self - social_schedulers
        if remaining:
            return super(EventMailScheduler, remaining)._execute_event_based()

    def _filter_template_ref(self):
        """ Check for valid template reference: existing, working template """
        valid = super()._filter_template_ref()
        invalid = valid.filtered(
            lambda scheduler: scheduler.notification_type == "social_post" and not scheduler.template_ref.account_ids
        )
        for scheduler in invalid:
            _logger.warning(
                "Cannot process scheduler %s (event %s - ID %s) as it refers to social post template %s (ID %s) that has no linked accounts",
                scheduler.id, scheduler.event_id.name, scheduler.event_id.id,
                scheduler.template_ref.name, scheduler.template_ref.id)
        return valid - invalid

    def _template_model_by_notification_type(self):
        info = super()._template_model_by_notification_type()
        info["social_post"] = "social.post.template"
        return info
