# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import models
from odoo.addons.web.models.models import lazymapping
from odoo.addons.mail.tools.discuss import Store


class BusSyncMixin(models.AbstractModel):
    _name = "bus.sync.mixin"
    _description = "Mixin for Bus Sync"

    def _sync_field_names(self, res):
        """
        Fill the field names to sync in res. Override in specific models.
        Keys are bus subchannel or (main channel_id, subchannel) names, values are Store.FieldList to sync.
        """

    def _store_sync_extra_fields(self, res: Store.FieldList):
        """
        Fill extra field names to sync in res. Override in specific models.
        :param res: list of field names that will be sync
        """

    def write(self, vals):
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
            result = defaultdict(dict)
            for bus_target, field_descriptions in fields_to_sync.items():
                target = (
                    (record[bus_target[0]], bus_target[1])
                    if isinstance(bus_target, tuple)
                    else (record._bus_channel(), bus_target)
                )
                result[target] = {
                    Store.get_field_name(field_description): (
                        get_field_value(record, field_description),
                        field_description,
                    )
                    for field_description in field_descriptions
                }
            return result

        self._sync_field_names(fields_to_sync := defaultdict(Store.FieldList))
        old_vals = {record: get_vals(record) for record in self}
        result = super().write(vals)
        stores = lazymapping(lambda param: Store(bus_channel=param[0], bus_subchannel=param[1]))
        for record in self:
            for (channels, subchannel), values in get_vals(record).items():
                diff = defaultdict(Store.FieldList)
                for field_name, (value, field_description) in values.items():
                    if value != old_vals[record][channels, subchannel][field_name][0]:
                        diff[channels, subchannel].append(field_description)
                if diff:
                    for (channels, subchannel), diff_fields in diff.items():
                        for channel in channels:
                            stores[channel, subchannel].add(
                                record,
                                lambda res, diff_fields=diff_fields: (
                                    res.extend(diff_fields),
                                    res.from_method("_store_sync_extra_fields"),
                                ),
                            )
        for store in stores.values():
            store.bus_send()
        return result
