/* @odoo-module */

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
        this.rpc = services.rpc;
        this.orm = services.orm;
        this.userSettingsService = services["mail.user_settings"];
        this.router = services.router;
        this.isReady = new Deferred();
        this.imStatusService = services.im_status;
        const user = services.user;
        this.store.Persona.insert({ id: user.partnerId, type: "partner", isAdmin: user.isAdmin });
        this.store.discuss.inbox = {
            id: "inbox",
            model: "mail.box",
            name: _t("Inbox"),
            type: "mailbox",
        };
        this.store.discuss.starred = {
            id: "starred",
            model: "mail.box",
            name: _t("Starred"),
            type: "mailbox",
            counter: 0,
        };
        this.store.discuss.history = {
            id: "history",
            model: "mail.box",
            name: _t("History"),
            type: "mailbox",
            counter: 0,
        };
        this.updateImStatusRegistration();
    }

    /**
     * Import data received from init_messaging
     */
    async initialize() {
        await this.rpc("/mail/init_messaging", {}, { silent: true }).then(
            this.initMessagingCallback.bind(this)
        );
    }

    initMessagingCallback(data) {
        if (data.current_partner) {
            this.store.user = { ...data.current_partner, type: "partner" };
        }
        if (data.currentGuest) {
            this.store.guest = {
                ...data.currentGuest,
                type: "guest",
            };
        }
        this.store.odoobot = { ...data.odoobot, type: "partner" };
        const settings = data.current_user_settings;
        this.userSettingsService.updateFromCommands(settings);
        this.userSettingsService.id = settings.id;
        this.store.companyName = data.companyName;
        this.store.discuss.inbox.counter = data.needaction_inbox_counter;
        this.store.internalUserGroupId = data.internalUserGroupId;
        this.store.discuss.starred.counter = data.starred_counter;
        this.store.mt_comment_id = data.mt_comment_id;
        this.store.discuss.isActive =
            data.menu_id === this.router.current.hash?.menu_id ||
            this.router.hash?.action === "mail.action_discuss";
        this.store.CannedResponse.insert(data.shortcodes ?? []);
        this.store.hasLinkPreviewFeature = data.hasLinkPreviewFeature;
        this.store.initBusId = data.initBusId;
        this.store.odoobotOnboarding = data.odoobotOnboarding;
        this.isReady.resolve(data);
        this.store.isMessagingReady = true;
        this.store.hasMessageTranslationFeature = data.hasMessageTranslationFeature;
    }

    /** @deprecated */
    get registeredImStatusPartners() {
        return this.store.registeredImStatusPartners;
    }

    /** @deprecated */
    updateImStatusRegistration() {}

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
        "rpc",
        "orm",
        "user",
        "router",
        "im_status",
        "mail.attachment", // FIXME: still necessary until insert is managed by this service
        "mail.user_settings",
        "mail.thread", // FIXME: still necessary until insert is managed by this service
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
