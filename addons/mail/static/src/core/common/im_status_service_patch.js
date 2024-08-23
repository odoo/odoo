/* @odoo-module */

import { AWAY_DELAY, imStatusService } from "@bus/im_status_service";
import { patch } from "@web/core/utils/patch";

export const imStatusServicePatch = {
    dependencies: [...imStatusService.dependencies, "mail.store"],

    start(env, services) {
        const { bus_service, "mail.store": store, presence } = services;
        const API = super.start(env, services);

        bus_service.subscribe(
            "bus.bus/im_status_updated",
            ({ im_status, partner_id, guest_id }) => {
                const persona = store.Persona.get({
                    type: partner_id ? "partner" : "guest",
                    id: partner_id ?? guest_id,
                });
                if (!persona) {
                    return; // Do not store unknown persona's status
                }
                persona.im_status = im_status;
                if (persona.type !== "guest" || persona.notEq(store.self)) {
                    return; // Partners are already handled by the original service
                }
                const isOnline = presence.getInactivityPeriod() < AWAY_DELAY;
                if ((im_status === "away" && isOnline) || im_status === "offline") {
                    this.updateBusPresence();
                }
            }
        );
        return API;
    },
};
export const unpatchImStatusService = patch(imStatusService, imStatusServicePatch);
