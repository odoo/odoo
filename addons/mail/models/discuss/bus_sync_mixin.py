# Part of Odoo. See LICENSE file for full copyright and licensing details.

import copy

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
        stores = Store.Stores()
        manager_by_bus_target = lazymapping(
            lambda bus_target: Store.FieldListManager(stores, self, bus_target),
        )
        self._sync_field_names(manager_by_bus_target)
        get_vals = Store.FieldListManager.get_val_by_field_by_store_by_record
        old_val_by_field_by_store_by_record = get_vals(manager_by_bus_target.values(), self)
        result = super().write(vals)
        new_val_by_field_by_store_by_record = get_vals(manager_by_bus_target.values(), self)
        for record in self:
            for store, new_vals_by_field in new_val_by_field_by_store_by_record[record].items():
                field_list = Store.FieldList(store, record)
                for field, new_value in new_vals_by_field.items():
                    if new_value != old_val_by_field_by_store_by_record[record][store][field]:
                        # Copy to avoid sharing the same Store.Attr for multiple stores/records.
                        # Store.Many for instance mutates self.sort to None after sorting records,
                        # which would cause incorrect behavior if the same instance is reused.
                        field_list.append(copy.copy(field))
                if field_list:
                    record._store_sync_extra_fields(field_list)
                    store.add(record, field_list)
        stores.bus_send()
        return result
