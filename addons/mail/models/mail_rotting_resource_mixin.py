# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields
from datetime import timedelta


class RottingResourceMixin(models.AbstractModel):
    _name = 'mail.rotting.resource.mixin'
    _description = 'Mixin for resources that can rot. Needs to be related to a mail.rotting.stage.mixin'

    _inherit = ['mail.thread']

    date_rot = fields.Date('Last activity', compute="_compute_date_rot", store=True)
    is_rotting = fields.Boolean('Rotting', compute='_compute_rotting')
    day_rotting = fields.Integer('Days Rotting', help='Day count since this resource was last updated',
        compute='_compute_rotting')
    # existence check: the parent model needs a stage_id (inheriting from the stage mixin?)
    stage_id = fields.Many2one('mail.rotting.stage.mixin')
    day_rot = fields.Integer(related='stage_id.day_rot')

    @api.depends('message_ids', 'write_date', 'stage_id.day_rot')
    def _compute_date_rot(self):
        for resource in self:
            # should only fetch the first message with types Email Outgoing or Comment (or Notification, for completed activities)
            last_message = next(
                (
                    message for message in resource.message_ids if message.message_type in ['email_outgoing', 'comment', 'notification']
                ), False
            )
            if last_message and resource.write_date:
                last_activity = max(last_message.date, resource.write_date).date()
            else:
                last_activity = resource.write_date or fields.Date.today()
            resource.date_rot = last_activity + timedelta(days=resource.day_rot)

    @api.depends('date_rot', 'day_rot', 'write_date', 'message_ids')
    def _compute_rotting(self):
        for resource in self:
            if self._resource_is_not_rotting_hook(resource):
                resource.is_rotting = False
                resource.day_rotting = 0
            else:
                resource.is_rotting = True
                resource.day_rotting = (fields.Date.today() - resource.date_rot).days + resource.stage_id.day_rot

    def _resource_is_not_rotting_hook(self, resource) -> bool:
        """
        :param resource
        :return: True if the resource is fresh

        Override this hook to add new conditions for which the resource is not rotting
        (e.g. the resource not being of a type that can rot, or being in a "finish" condition.)
        Don't forget to also override _compute_rotting with the new @api.depends, based on the fields you use
        """
        return resource.day_rot == 0 or fields.Date.today() < resource.date_rot
