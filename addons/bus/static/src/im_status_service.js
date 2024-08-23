/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { session } from "@web/session";

export const AWAY_DELAY = 30 * 60 * 1000; // 30 minutes
export const FIRST_UPDATE_DELAY = 500;
export const UPDATE_BUS_PRESENCE_DELAY = 60000;

/**
 * This service updates periodically the user presence in order for the
 * im_status to be up to date.
 */
export const imStatusService = {
    dependencies: ["bus_service", "presence"],

    start(env, { bus_service, presence }) {
        let lastSentInactivity;
        let becomeAwayTimeout;

        const updateBusPresence = () => {
            lastSentInactivity = presence.getInactivityPeriod();
            startAwayTimeout();
            bus_service.send("update_presence", {
                inactivity_period: lastSentInactivity,
                im_status_ids_by_model: {},
            });
        };
        this.updateBusPresence = updateBusPresence;

        const startAwayTimeout = () => {
            clearTimeout(becomeAwayTimeout);
            const awayTime = AWAY_DELAY - lastSentInactivity;
            if (awayTime > 0) {
                becomeAwayTimeout = browser.setTimeout(() => updateBusPresence(), awayTime);
            }
        };
        bus_service.addEventListener("connect", () => updateBusPresence(), { once: true });
        bus_service.subscribe("bus.bus/im_status_updated", async ({ partner_id, im_status }) => {
            if (session.is_public || !partner_id || partner_id !== user.partnerId) {
                return;
            }
            const isOnline = presence.getInactivityPeriod() < AWAY_DELAY;
            if (im_status === "offline" || (im_status === "away" && isOnline)) {
                this.updateBusPresence();
            }
        });
        presence.bus.addEventListener("presence", () => {
            if (lastSentInactivity >= AWAY_DELAY) {
                this.updateBusPresence();
            }
            startAwayTimeout();
        });
    },
};

registry.category("services").add("im_status", imStatusService);
