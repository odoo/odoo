# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResUsersSettings(models.Model):
    _inherit = "res.users.settings"

    # Calendar module settings.
    calendar_default_privacy = fields.Selection(
        [('public', 'Public'),
         ('private', 'Private'),
         ('confidential', 'Only internal users')],
        'Calendar Default Privacy', default='public', required=True,
        store=True, readonly=False, help="Default privacy setting for whom the calendar events will be visible."
    )

    @api.model
    def _get_fields_blacklist(self):
        """ Get list of calendar fields that won't be formatted in session_info. """
        calendar_fields_blacklist = ['calendar_default_privacy']
        return super()._get_fields_blacklist() + calendar_fields_blacklist
