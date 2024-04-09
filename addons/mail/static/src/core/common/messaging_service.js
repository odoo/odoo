import { cleanTerm } from "@mail/utils/common/format";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Deferred } from "@web/core/utils/concurrency";

export class Messaging {
    constructor(...args) {
        this.setup(...args);
    }

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    setup(env, services) {
        this.env = env;
        this.store = services["mail.store"];
        this.orm = services.orm;
        this.isReady = new Deferred();
        this.store.discuss.inbox = {
            id: "inbox",
            model: "mail.box",
            name: _t("Inbox"),
        };
        this.store.discuss.starred = {
            id: "starred",
            model: "mail.box",
            name: _t("Starred"),
            counter: 0,
        };
        this.store.discuss.history = {
            id: "history",
            model: "mail.box",
            name: _t("History"),
            counter: 0,
        };
    }

    get initMessagingParams() {
        return {
            init_messaging: {},
        };
    }

    /**
     * Import data received from init_messaging
     */
    async initialize() {
        await this.store.fetchData(this.initMessagingParams, { readonly: false });
        this.isReady.resolve();
    }

    // -------------------------------------------------------------------------
    // actions that can be performed on the messaging system
    // -------------------------------------------------------------------------

    /**
     * @return {import("models").Persona[]}
     */
    async searchPartners(searchStr = "", limit = 10) {
        const partners = [];
        const searchTerm = cleanTerm(searchStr);
        for (const localId in this.store.Persona.records) {
            const persona = this.store.Persona.records[localId];
            if (persona.type !== "partner") {
                continue;
            }
            const partner = persona;
            // todo: need to filter out non-user partners (there was a user key)
            // also, filter out inactive partners
            if (partner.name && cleanTerm(partner.name).includes(searchTerm)) {
                partners.push(partner);
                if (partners.length >= limit) {
                    break;
                }
            }
        }
        if (!partners.length) {
            const partnersData = await this.orm.silent.call("res.partner", "im_search", [
                searchTerm,
                limit,
            ]);
            this.store.Persona.insert(partnersData);
        }
        return partners;
    }

    openDocument({ id, model }) {
        this.env.services.action.doAction({
            type: "ir.actions.act_window",
            res_model: model,
            views: [[false, "form"]],
            res_id: id,
        });
    }
}

export const messagingService = {
    dependencies: [
        "mail.store",
        "orm",
        "im_status",
        "mail.attachment", // FIXME: still necessary until insert is managed by this service
        "mail.message", // FIXME: still necessary until insert is managed by this service
        "mail.persona", // FIXME: still necessary until insert is managed by this service
    ],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        const messaging = new Messaging(env, services);
        messaging.initialize();
        return messaging;
    },
};

registry.category("services").add("mail.messaging", messagingService);
