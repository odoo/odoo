/* @odoo-module */

import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useSequential } from "@mail/utils/common/hooks";
import { markRaw } from "@odoo/owl";

export const DEFAULT_AVATAR = "/mail/static/src/img/smiley/avatar.jpg";

export class PersonaService {
    constructor(...args) {
        this.setup(...args);
    }

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    setup(env, services) {
        this.env = env;
        this.orm = services.orm;
        /** @type {import("@mail/core/common/store_service").Store} */
        this.store = services["mail.store"];
        this.sequential = useSequential();
        /** Queue used for handling sequential of fetching is_company of persona */
        this._sQueue = markRaw({
            /** @type {Set<number>} */
            todo: new Set(),
        });
    }

    async updateGuestName(guest, name) {
        await rpc("/mail/guest/update_name", {
            guest_id: guest.id,
            name,
        });
    }

    /**
     * List of known partner ids with a direct chat, ordered
     * by most recent interest (1st item being the most recent)
     *
     * @returns {[integer]}
     */
    getRecentChatPartnerIds() {
        return Object.values(this.store.Thread.records)
            .filter((thread) => thread.type === "chat")
            .sort((a, b) => {
                const [a_dt, b_dt] = [a.lastInterestDateTime, b.lastInterestDateTime];
                if (!a_dt && !b_dt) {
                    return 0;
                }
                if (a_dt && !b_dt) {
                    return -1;
                }
                if (!a_dt && b_dt) {
                    return 1;
                }
                return b_dt.ts - a_dt.ts;
            })
            .map((thread) => thread.correspondent?.id);
    }

    updateUserNotificationPreference({ id, notification_preference }) {
        if (this.store.self.user.id !== id) {
            return;
        }
        this.store.self.notification_preference = notification_preference;
    }
}

export const personaService = {
    dependencies: ["orm", "mail.store"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        return new PersonaService(env, services);
    },
};

registry.category("services").add("mail.persona", personaService);
