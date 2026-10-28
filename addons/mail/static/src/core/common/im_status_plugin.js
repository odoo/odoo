import { BusPlugin } from "@bus/services/bus_plugin";
import { PresencePlugin } from "@bus/services/presence_plugin";

import { onWillDestroy, Plugin, useListener, usePlugin } from "@odoo/owl";
import { services } from "@web/core/services";

export const AWAY_DELAY = 30 * 60 * 1000; // 30 minutes

/**
 * This plugin keeps the user's presence up to date with the server. When the
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
    /** @private */
    bus = usePlugin(BusPlugin);
    /** @private */
    presence = usePlugin(PresencePlugin);
    /** @private */
    lastSentInactivity;
    /** @private */
    becomeAwayTimeout;

    setup() {
        const onConnect = () => {
            this.bus.removeEventListener("BUS:CONNECT", onConnect);
            this.updateBusPresence();
        };
        this.bus.addEventListener("BUS:CONNECT", onConnect);
        useListener(this.presence.bus, "presence", () => {
            if (this.lastSentInactivity === undefined || this.lastSentInactivity >= AWAY_DELAY) {
                this.updateBusPresence();
            }
            this.startAwayTimeout();
        });
        onWillDestroy(() => {
            this.bus.removeEventListener("BUS:CONNECT", onConnect);
            clearTimeout(this.becomeAwayTimeout);
        });
    }

    updateBusPresence() {
        this.lastSentInactivity = this.presence.getInactivityPeriod();
        this.startAwayTimeout();
        this.bus.send("update_presence", { inactivity_period: this.lastSentInactivity });
    }

    /** @private */
    startAwayTimeout() {
        clearTimeout(this.becomeAwayTimeout);
        const awayTime = AWAY_DELAY - this.presence.getInactivityPeriod();
        if (awayTime > 0) {
            this.becomeAwayTimeout = setTimeout(() => this.updateBusPresence(), awayTime);
        }
    }
}

services.add(ImStatusPlugin);
