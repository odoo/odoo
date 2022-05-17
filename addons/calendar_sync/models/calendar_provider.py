# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from typing import List
from odoo import fields, models, api
from odoo.addons.calendar_sync.utils.event import ProviderData, ProviderEvents, ProviderEvent

class AbstractCalendarProvider(models.Model):
    """
    This module provides the interface to implement to support a new calendar provider
    such as Microsoft or Google.
    It also already handles all sync stuff which are common to all providers.
    """
    _name = 'calendar.provider'

    syncer_id = fields.Many2one('calendar.syncer')

    @api.model
    def _sync(self):
        """
        Do the whole synchronization of events between the Odoo calendar of the user and
        an external calendar provider selected by this user.
        """
        provider_data = self.get_events_to_sync()
        self._sync_removed_events(provider_data.removed)
        self._sync_added_events(provider_data.added)
        self.sync_updated_events(provider_data.updated)

    @api.model
    def _sync_removed_events(self, data: ProviderEvents):
        """
        Synchronize events which have been removed from the provider side.
        """
        self._sync_removed_recurrences(data.recurrences)
        self._sync_removed_single_events(data.singles)

    @api.model
    def _sync_removed_single_events(self, events: List[ProviderEvent]):
        """
        Synchronize single events which have been removed from the provider side.        
        """
        odoo_events = self.env['calendar.event'].browse(
            e.get_odoo_event() for e in events if e.has_odoo_event()
        )
        odoo_events.unlink()

    @api.model
    def _sync_removed_recurrences(self, recurrences: List[ProviderEvent]):
        """
        Synchronize recurrent events which have been removed from the provider side.
        """
        odoo_recurrences = self.env['calendar.recurrence'].browse(
            r.get_odoo_event() for r in recurrences if r.has_odoo_event()
        )
        odoo_recurrences.unlink()

    @api.model
    def _sync_updated_events(self, data: ProviderEvents):
        """
        Synchronize events which have been updated from the provider side.
        """
        # TODO: handle cancelled events
        pass

    @api.model
    def _sync_added_events(self, data: ProviderEvents):
        """
        Synchronize events which have been added from the provider side.
        """
        self._sync_added_recurrences(data.recurrences)
        self._sync_added_single_events(data.singles)

    @api.model
    def _sync_added_single_events(self, events: List[ProviderEvent]):
        """
        Synchronize single events which have been added from the provider side.
        """
        values = [self._to_odoo_event_values(e) for e in events]
        self._create_odoo_events(values)

    @api.model
    def _sync_added_recurrences(self, recurrences: List[ProviderEvent]):
        """
        Synchronize recurrent events which have been added from the provider side.
        """
        values = [self._to_odoo_recurrence_values(r) for r in recurrences]
        self._create_odoo_recurrences(values)

    @api.model
    def _create_odoo_events(self, values):
        self.env['calendar.event'].create(values)

    @api.model
    def _create_odoo_recurrences(self, values):
        self.env['calendar.recurrence'].create(values)

    @api.model
    def _pack_provider_data(
        self, all_events, mapped_events: List[ProviderEvent], mapped_recurrences: List[ProviderEvent]
    ) -> ProviderData:
        """
        Pack events to sync in a dedicated structure (ProviderData) sorted by
        kind of update (added, updated, removed) and then by kind of events
        (single or recurrence).
        """
        def _filter(fn, it):
            return tuple(filter(fn, it))

        def _new(mapped):
            def f(event):
                return event.id not in (event.id for e in mapped)
            return f

        self.ensure_one()
        events = (e for e in all_events if not e.is_recurrence())
        recurrences = (e for e in all_events if e.is_recurrence())

        return ProviderData(
            added=ProviderEvents(
                singles=_filter(_new(mapped_events), events),
                recurrences=_filter(_new(mapped_recurrences), recurrences),
            ),
            updated=ProviderEvents(
                singles=_filter(lambda e: not e.is_removed(), mapped_events),
                recurrences=_filter(lambda r: not r.is_removed(), mapped_recurrences),
            ),
            removed=ProviderEvents(
                singles=_filter(lambda e: e.is_removed(), mapped_events),
                recurrences=_filter(lambda r: r.is_removed(), mapped_recurrences),
            ),
        )

    # ----------------------------------------------------------------------------------
    # Method to override to implement your own events provider
    # ----------------------------------------------------------------------------------

    def get_events_to_sync(self) -> ProviderData:
        """
        Get the list of events to sync from the provider.
        This method must pack events to sync with the method `_pack_provider_data` to
        return a clean ProviderData named tuple.
        """
        raise Exception("Not overriden")

    @api.model
    def _to_odoo_event_values(self, event: ProviderEvent) -> dict:
        """
        Convert an event from provider format to Odoo format.
        """
        raise Exception("Not overriden")

    @api.model
    def _to_odoo_recurrence_values(self, recurrence: ProviderEvent) -> dict:
        """
        Convert recurrences from provider format to Odoo format.
        """
        raise Exception("Not overriden")

    # def create_events_from_provider(provider, provider_events):
    #     """
    #     Create Odoo events and recurrences from new single events and recurrences of the provider.
    #     """
    #     provider.create_odoo_events([
    #         e.odoo_values()
    #         for e in provider_events
    #         if not e.odoo_id and e.is_single_event()
    #     ])
    #     provider.create_odoo_recurrences([
    #         e.odoo_values()
    #         for e in provider_events
    #         if not e.odoo_id and e.is_recurrence()
    #     ])

    # def create_events_from_odoo(provider):
    #     events = self.env['calendar.event'].search(provider.get_new_event_domain())
    #     provider.create_events([Event.from_odoo_values(e) for e in events])

    #     recurrences = self.env['calendar.recurrence'].search(provider.get_new_recurrence_domain())
    #     provider.create_recurrences([Event.from_odoo_values(r) for r in recurrences])

    #     # 1) récupérer les events du provider (api call)
    #     # 2) mapper les events récupérés avec les events odoo
    #     # 3) sync:
    #     #    - supprimer les events (tout type) qui n'existe plus chez le provider
    #     #    - supprimer les events (tout type) qui n'existe plus chez Odoo
    #     #    - mettre à jour les events (tout type) pour les modifs non structurelles (pas time-based)
    #     #    - mettre à jour les events (récurrence, partie de récurrence) pour les modifs structurelles
    #     #    - création des nouveaux events simples
    #     #    - création des nouvelles récurrences (avec recyclage des events orphans (voir mise à jour))


    #     # TODO:
    #     #    - 



    # def sync_to_provider(self, provider):
    #     pass




    # TODO: steps
    # 1) ajouter la synchronisation

    # TODO: synchronizer
    #   use cases:
    #       * a single event from/to provider
    #           insert
    #           update
    #           remove 
    #       * the whole recurrence
    #           insert
    #           update
    #               => not time-based => patch the whole recurrence
    #               => time-based => delete old, create a new one
    #           remove
    #       * an event from a recurrence
    #           update : create an exception in still attached to the recurrence
    #           remove
    #       * several events from a recurrence
    #           update
    #               => not time-base =>
    #                   => create an exception still attached to the recurrence
    #               => time based =>
    #                   => update the current recurrence (and make some event orphans)
    #                   => create a new one (and try to recycle orphan events if possible)
    #           remove
    #
    # IMPORTANTS: need to know if the modification is time-based or not

    # critical points:
    #   - updated time-base fields of a recurrence leads to split it in 2 parts.

    # TODO:
    # - provide events in a standard format to synchronizer
    # - provide interfaces to:
    #    - add, update, delete an simple event
    #    - add, update, delete a recurrence
    #    - manage attendees