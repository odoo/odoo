import { BusPlugin } from "@bus/services/bus_plugin";
import { PresencePlugin } from "@bus/services/presence_plugin";
import { Plugin, usePlugin } from "@odoo/owl";
import { registry } from "@web/core/registry";

export const AWAY_DELAY = 30 * 60 * 1000; // 30 minutes

/**
 * This service keeps the user's presence up to date with the server. When the
 * connection to the server is established, the user's presence is updated. If
 * another device or browser updates the user's presence, the presence is sent to
 * the server if relevant (e.g., another device is away or offline, but this one
 * is online).
 *
 * To receive updates through the bus, subscribe to presence channels
 * (e.g., subscribe to `odoo-presence-res.users_3-token` to receive updates about
 * this user). Token is optional and can be used to grant access to the presence
 * channel if the user is not allowed to read the other user's presence.
 * See `_get_im_status_access_token`.
 */
export class ImStatusPlugin extends Plugin {
    busPlugin = usePlugin(BusPlugin);
    presence = usePlugin(PresencePlugin);

    becomeAwayTimeout = null;
    lastSentInactivity = null;

    setup() {
        this.busPlugin.addEventListener("BUS:CONNECT", () => this.updateBusPresence(), {
            once: true,
        });
        this.presence.bus.addEventListener("presence", () => {
            if (!this.lastSentInactivity || this.lastSentInactivity >= AWAY_DELAY) {
                this.updateBusPresence();
            }
            this._startAwayTimeout();
        });
    }

    updateBusPresence() {
        this.lastSentInactivity = this.presence.getInactivityPeriod();
        this._startAwayTimeout();
        this.busPlugin.send("update_presence", { inactivity_period: this.lastSentInactivity });
    }

    /**
     * @private
     */
    _startAwayTimeout() {
        clearTimeout(this.becomeAwayTimeout);
        const awayTime = AWAY_DELAY - this.presence.getInactivityPeriod();
        if (awayTime > 0) {
            this.becomeAwayTimeout = setTimeout(() => this.updateBusPresence(), awayTime);
        }
    }
}

/**
 * ----------------------------------------------------------------------------
 * @todo owl3 migration
 * Temporary - to remove when all uses of the "im_status" service are removed
 * ----------------------------------------------------------------------------
 */
registry.category("services").add("im_status", {
    start() {
        return usePlugin(ImStatusPlugin);
    },
});
