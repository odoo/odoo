import { browser } from "@web/core/browser/browser";
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
 * (e.g., subscribe to `odoo-presence-res.partner_3-token` to receive updates about
 * this partner). Token is optional and can be used to grant access to the presence
 * channel if the user is not allowed to read the partner's presence.
 * See `_get_im_status_access_token`.
 */
export const imStatusService = {
    dependencies: ["bus_service", "presence"],
    // and cyclic dependecy with "mail.store" (both services should be merged together)

    start(env, { bus_service, presence }) {
        let lastSentInactivity;
        let becomeAwayTimeout;

        const updateBusPresence = () => {
            lastSentInactivity = presence.getInactivityPeriod();
            startAwayTimeout();
            bus_service.send("update_presence", { inactivity_period: lastSentInactivity });
        };

        const startAwayTimeout = () => {
            clearTimeout(becomeAwayTimeout);
            const awayTime = AWAY_DELAY - presence.getInactivityPeriod();
            if (awayTime > 0) {
                becomeAwayTimeout = browser.setTimeout(() => updateBusPresence(), awayTime);
            }
        };
        bus_service.addEventListener("BUS:CONNECT", () => updateBusPresence(), { once: true });
        bus_service.subscribe(
            "bus.bus/im_status_updated",
            async ({ presence_status, im_status, partner_id, guest_id, debounce = true }) => {
                const store = env.services["mail.store"];
                const partner = store["res.partner"].get(partner_id);
                const guest = store["mail.guest"].get(guest_id);
                if (!partner && !guest) {
                    return; // Do not store unknown persona's status
                }
                if (debounce) {
                    partner?.debouncedSetImStatus(im_status);
                    guest?.debouncedSetImStatus(im_status);
                } else {
                    partner?.updateImStatus(im_status);
                    guest?.updateImStatus(im_status);
                }
                if (partner?.eq(store.self_partner) || guest?.eq(store.self_guest)) {
                    const isOnline = presence.getInactivityPeriod() < AWAY_DELAY;
                    if ((presence_status === "away" && isOnline) || presence_status === "offline") {
                        updateBusPresence();
                    }
                }
            }
        );
        presence.bus.addEventListener("presence", () => {
            if (!lastSentInactivity || lastSentInactivity >= AWAY_DELAY) {
                updateBusPresence();
            }
            startAwayTimeout();
        });
        return { updateBusPresence };
    },
};

registry.category("services").add("im_status", imStatusService);
