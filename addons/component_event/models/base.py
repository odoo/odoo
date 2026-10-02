# Copyright 2017 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""
Base Model
==========

Extend the 'base' Odoo Model to add Events related features.


"""

from odoo import api, models

from odoo.addons.component.core import _component_databases

from ..components.event import CollectedEvents
from ..core import EventWorkContext


class Base(models.AbstractModel):
    """The base model, which is implicitly inherited by all models.

    Add an :meth:`_event` method to all Models. This method allows to
    trigger events.

    It also notifies the following events:

    * ``on_record_create(self, record, fields=None)``
    * ``on_record_write(self, record, fields=none)``
    * ``on_record_unlink(self, record)``

    ``on_record_unlink`` is notified just *before* the unlink is done.

    """

    _inherit = "base"

    def _event(self, name, collection=None, components_registry=None):
        """Collect events for notifications

        Usage::

            def button_do_something(self):
                for record in self:
                    # do something
                    self._event('on_do_something').notify('something')

        With this line, every listener having a ``on_do_something`` method
        with be called and receive 'something' as argument.

        See: :mod:`..components.event`

        :param name: name of the event, start with 'on_'
        :param collection: optional collection  to filter on, only
                           listeners with similar ``_collection`` will be
                           notified
        :param components_registry: component registry for lookups,
                                    mainly used for tests
        :type components_registry:
            :class:`odoo.addons.components.core.ComponentRegistry`


        """
        dbname = self.env.cr.dbname
        components_registry = self.env.context.get(
            "components_registry", components_registry
        )
        comp_registry = components_registry or _component_databases.get(dbname)
        if not comp_registry or not comp_registry.ready:
            # No event should be triggered before the registry has been loaded
            # This is a very special case, when the odoo registry is being
            # built, it calls odoo.modules.loading.load_modules().
            # This function might trigger events (by writing on records, ...).
            # But at this point, the component registry is not guaranteed
            # to be ready, and anyway we should probably not trigger events
            # during the initialization. Hence we return an empty list of
            # events, the 'notify' calls will do nothing.
            return CollectedEvents([])
        if not comp_registry.get("base.event.collecter"):
            return CollectedEvents([])

        model_name = self._name
        if collection is not None:
            work = EventWorkContext(
                collection=collection,
                model_name=model_name,
                components_registry=components_registry,
            )
        else:
            work = EventWorkContext(
                env=self.env,
                model_name=model_name,
                components_registry=components_registry,
            )

        collecter = work._component_class_by_name("base.event.collecter")(work)
        return collecter.collect_events(name)

    @api.model_create_multi
    def create(self, vals_list):
        records = super(Base, self).create(vals_list)
        for idx, vals in enumerate(vals_list):
            fields = list(vals.keys())
            self._event("on_record_create").notify(records[idx], fields=fields)
        return records

    def write(self, vals):
        result = super(Base, self).write(vals)
        fields = list(vals.keys())
        for record in self:
            self._event("on_record_write").notify(record, fields=fields)
        return result

    def unlink(self):
        for record in self:
            self._event("on_record_unlink").notify(record)
        result = super(Base, self).unlink()
        return result
