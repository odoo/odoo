# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime as dt
from collections import defaultdict

from odoo import api, fields, models
from odoo.tools import SQL, OrderedSet

from .bus import json_dump, send_notify_payloads

GC_RETENTION_SECONDS = 60 * 60


class BusSubscriptionChange(models.Model):
    _name = "bus.subscription.change"
    _description = "Bus Subscription Change"
    _log_access = False

    create_date = fields.Datetime(index=True)
    payload = fields.Json()

    @api.autovacuum
    def _gc_changes(self):
        timeout_ago = fields.Datetime.now() - dt.timedelta(seconds=GC_RETENTION_SECONDS)
        self.env.cr.execute(
            SQL("DELETE FROM bus_subscription_change WHERE create_date < %s", timeout_ago),
        )

    def _add_change(self, owners, gained=None, lost=None):
        """Make the websockets of ``owners`` (users, guests) subscribe to the bus channels of
        ``gained`` and leave those of ``lost`` once the transaction is committed, without the
        client. A gained channel catches up from the bus id at the first change of the
        transaction."""
        gained = tuple(sorted((record._name, record.id) for record in gained or ()))
        lost = tuple(sorted((record._name, record.id) for record in lost or ()))
        if not owners or not (gained or lost):
            return
        cr = self.env.cr
        if "bus.subscription.change" not in cr.precommit.data:
            cr.precommit.data["bus.subscription.change"] = {
                # sudo - bus.bus: reading the last bus id isn't sensitive.
                "last": self.env["bus.bus"].sudo()._bus_last_id(),
                "owner_ids_by_key": defaultdict(OrderedSet),
            }

            @cr.precommit.add
            def insert_changes():
                data = cr.precommit.data.pop("bus.subscription.change", None)
                if not data:
                    return
                for (owner_model, gained, lost), owner_ids in data["owner_ids_by_key"].items():
                    payload = {
                        "owner_model": owner_model,
                        "owner_ids": list(owner_ids),
                        "gained": gained,
                        "lost": lost,
                        "last": data["last"],
                    }
                    cr.execute(SQL(
                        """INSERT INTO bus_subscription_change (payload, create_date)
                           VALUES (%s, clock_timestamp() AT TIME ZONE 'UTC')""",
                        json_dump(payload),
                    ))
                cr.postcommit.add(
                    lambda: send_notify_payloads("imbus_subscription", [json_dump(cr.dbname)]),
                )

        owner_ids_by_key = cr.precommit.data["bus.subscription.change"]["owner_ids_by_key"]
        owner_ids_by_key[owners._name, gained, lost].update(owners.ids)
