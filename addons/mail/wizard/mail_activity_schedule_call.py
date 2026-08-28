# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailActivityScheduleCall(models.TransientModel):
    """ The activity scheduling wizard, as opened to log a call that took place on the
    document of the user's choice. """
    _name = 'mail.activity.schedule.call'
    _inherit = 'mail.activity.schedule'
    _description = 'Log a call as an activity in a chatter'

    is_call_ongoing = fields.Boolean(
        compute='_compute_is_call_ongoing', export_string_translation=False)

    def _compute_is_call_ongoing(self):
        """ Whether the call being logged is still going on, which a module with a call
        of its own tells by overriding this. """
        self.is_call_ongoing = False
