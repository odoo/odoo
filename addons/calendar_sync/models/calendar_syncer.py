# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import fields, models, api

_logger = logging.getLogger(__name__)


class CalendarSyncer(models.Model):
    """
    The calendar syncer manages the interface with the front-end (calendar views) and is responsible
    for syncing the Odoo calendar of a Odoo user, to a calendar of an external provider such as Microsoft or Google,
    owned by this same user.
    Note that there is only one instance of calendar syncer (singleton).
    All providers are registered to this single instance but only the provider selected by the current user is used
    to sync with the Odoo calendar.
    """
    _name = 'calendar.syncer'

    provider_ids = fields.One2many(
        string="List of available calendar providers",
        comodel_name='calendar.provider',
        inverse_name='syncer_id'
    )

    @api.model
    def get_syncer(self):
        """
        Returns the unique instance of calendar syncer.
        """
        return self.env.ref('calendar_sync.calendar_syncer')

    def _get_provider_from_name(self, provider_name):
        """
        Get a provider instance from its name.
        """
        provider = self.provider_ids.filtered(lambda p: p.get_name() == provider_name)
        return provider[0] if provider else None

    def sync(self):
        """
        Do the whole synchronization of events between the Odoo calendar of the user and
        the external calendar provider selected by this user.
        """
        current_user = self.env.user
        provider = self._get_provider_from_name(current_user.calendar_provider_name)

        if provider:
            provider._sync()
