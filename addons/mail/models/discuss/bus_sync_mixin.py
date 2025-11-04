# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import models, api
from odoo.addons.web.models.models import lazymapping
from odoo.addons.mail.tools.discuss import Store


class BusSyncMixin(models.AbstractModel):
    _name = "bus.sync.mixin"
    _description = "Mixin for Bus Sync"

    @api.model
    def _sync_field_names(self):
        """
        Return the field names to sync. Override in specific models.
        Keys are bus subchannel names, values are lists of field names to sync.
        """
        return defaultdict(list)

    @api.model
    def _sync_extra_field_names(self, target: Store.Target, fields):
        """
        Return the extra field names to sync. Override in specific models.
        :param target: the target to sync to (Store.Target)
        :param fields: list of field names that have changed
        """
        return []

    def write(self, vals):
        def get_field_name(field_description):
            if isinstance(field_description, Store.Attr):
                return field_description.field_name
            return field_description

        def get_field_value(record, field_description):
            """Get the value of a field based on its description."""
            if isinstance(field_description, Store.Attr):
                if field_description.predicate and not field_description.predicate(record):
                    return None
            if isinstance(field_description, Store.Relation):
                return field_description._get_value(record).records
            if isinstance(field_description, Store.Attr):
                return field_description._get_value(record)
            return record[field_description]

        def get_vals(record):
            """Get the current values of the fields to sync."""
            return {
                subchannel: {
                    get_field_name(field_description): (
                        get_field_value(record, field_description),
                        field_description,
                    )
                    for field_description in field_descriptions
                }
                for subchannel, field_descriptions in self._sync_field_names().items()
            }

        old_vals = {record: get_vals(record) for record in self}
        result = super().write(vals)
        stores = lazymapping(lambda param: Store(bus_channel=param[0], bus_subchannel=param[1]))
        for record in self:
            for subchannel, values in get_vals(record).items():
                diff = []
                for field_name, (value, field_description) in values.items():
                    if value != old_vals[record][subchannel][field_name][0]:
                        diff.append(field_description)
                if diff:
                    for channel in record._bus_channel():
                        stores[channel, subchannel].add(record, diff)
                        if extra_fields := record._sync_extra_field_names(stores[channel, subchannel].target, diff):
                            stores[channel, subchannel].add(record, extra_fields)
        for store in stores.values():
            store.bus_send()
        return result
