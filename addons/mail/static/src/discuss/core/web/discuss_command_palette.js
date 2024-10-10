import { cleanTerm } from "@mail/utils/common/format";

import { Component, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { ImStatus } from "@mail/core/common/im_status";
import { CreateThreadDialog } from "../public_web/create_thread_dialog";
import { useService } from "@web/core/utils/hooks";

const commandCategoryRegistry = registry.category("command_categories");
const commandSetupRegistry = registry.category("command_setup");
const commandProviderRegistry = registry.category("command_provider");

const DISCUSS_MENTIONED = "DISCUSS_MENTIONED";
const DISCUSS_RECENT = "DISCUSS_RECENT";

commandCategoryRegistry
    .add(DISCUSS_MENTIONED, { namespace: "@", name: _t("Mentions") }, { sequence: 10 })
    .add(DISCUSS_RECENT, { namespace: "@", name: _t("Recent") }, { sequence: 20 });

class DiscussCommand extends Component {
    static components = { ImStatus };
    static template = "mail.DiscussCommand";
    static props = {
        counter: { type: Number, optional: true },
        executeCommand: Function,
        icon: { String, optional: true },
        imgUrl: { String, optional: true },
        name: String,
        persona: { type: Object, optional: true },
        channel: { type: Object, optional: true },
        isAction: { type: Boolean, optional: true },
        searchValue: String,
        slots: Object,
    };

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.ui = useState(useService("ui"));
    }
}

// -----------------------------------------------------------------------------
// add @ namespace + provider
// -----------------------------------------------------------------------------
commandSetupRegistry.add("@", {
    debounceDelay: 200,
    emptyMessage: _t("No conversation found"),
    name: _t("conversations"),
    placeholder: _t("Search a conversation"),
});

export class DiscussCommandPalette {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} env.services
     */
    constructor(env, options) {
        this.env = env;
        this.options = options;
        this.dialog = env.services.dialog;
        /** @type {import("models").Store} */
        this.store = env.services["mail.store"];
        this.suggestion = env.services["mail.suggestion"];
        this.ui = env.services.ui;
        this.commands = [];
        this.options = options;
        this.cleanedTerm = cleanTerm(this.options.searchValue);
    }

    async fetch() {
        await this.store.channels.fetch();
        await this.store.searchConversations(this.cleanedTerm);
    }

    buildResults() {
        const needactionChannels = this.store.getNeedactionChannels();
        const recentChannels = this.store.getRecentChannels();
        const mentionedSet = new Set();
        const recentSet = new Set();
        const TOTAL_LIMIT = this.ui.isSmall ? 7 : 9;
        const CATEGORY_LIMIT = 3;
        if (!this.cleanedTerm) {
            const limitedMentioned = needactionChannels.slice(0, CATEGORY_LIMIT);
            for (const channel of limitedMentioned) {
                this.commands.push(this.makeDiscussCommand(channel, DISCUSS_MENTIONED));
                if (channel.channel_type === "chat") {
                    mentionedSet.add(channel.correspondent.persona);
                } else {
                    mentionedSet.add(channel);
                }
            }
            const limitedRecent = recentChannels.slice(0, CATEGORY_LIMIT);
            for (const channel of limitedRecent) {
                this.commands.push(this.makeDiscussCommand(channel, DISCUSS_RECENT));
                if (channel.channel_type === "chat") {
                    recentSet.add(channel.correspondent.persona);
                } else {
                    recentSet.add(channel);
                }
            }
        }
        const remaining = TOTAL_LIMIT - mentionedSet.size - recentSet.size;
        let personas = Object.values(this.store.Persona.records).filter(
            (persona) =>
                persona !== this.store.self &&
                persona.isInternalUser &&
                cleanTerm(persona.name).includes(this.cleanedTerm)
        );
        personas = this.suggestion
            .sortPartnerSuggestions(personas, this.cleanedTerm)
            .slice(0, TOTAL_LIMIT)
            .filter((persona) => !recentSet.has(persona) && !mentionedSet.has(persona));
        const channels = Object.values(this.store.Thread.records)
            .filter(
                (thread) =>
                    thread.channel_type &&
                    thread.channel_type !== "chat" &&
                    cleanTerm(thread.displayName).includes(this.cleanedTerm)
            )
            .slice(0, TOTAL_LIMIT)
            .filter((persona) => !recentSet.has(persona) && !mentionedSet.has(persona));
        // balance remaining: half personas, half channels
        const elligiblePersonas = [];
        const elligibleChannels = [];
        let i = 0;
        while ((channels.length || personas.length) && i < remaining) {
            const p = personas.shift();
            const c = channels.shift();
            if (p) {
                elligiblePersonas.push(p);
                i++;
            }
            if (i >= remaining) {
                break;
            }
            if (c) {
                elligibleChannels.push(c);
                i++;
            }
        }
        for (const persona of elligiblePersonas) {
            this.commands.push(this.makeDiscussCommand(persona));
        }
        for (const channel of elligibleChannels) {
            this.commands.push(this.makeDiscussCommand(channel));
        }
    }

    async openThread(thread) {
        switch (thread.channel_type) {
            case "chat":
                this.store.openChat({ partnerId: thread.correspondent.persona.id });
                break;
            case "group":
                thread.open();
                break;
            case "channel": {
                await this.store.joinChannel(thread.id, thread.name);
                thread.open();
            }
        }
    }

    makeDiscussCommand(threadOrPersona, category) {
        if (threadOrPersona?.Model?.name === "Thread") {
            /** @type {import("models").Thread} */
            const thread = threadOrPersona;
            return {
                Component: DiscussCommand,
                action: async () => this.openThread(thread),
                name: thread.displayName,
                category,
                props: {
                    imgUrl: thread.avatarUrl,
                    channel: thread.channel_type !== "chat" ? thread : undefined,
                    persona:
                        thread.channel_type === "chat" ? thread.correspondent.persona : undefined,
                    counter: thread.importantCounter,
                },
            };
        }
        if (threadOrPersona?.Model?.name === "Persona") {
            /** @type {import("models").Persona} */
            const persona = threadOrPersona;
            const chat = persona.searchChat();
            return {
                Component: DiscussCommand,
                action: () => {
                    this.store.openChat({ partnerId: persona.id });
                },
                name: persona.name,
                category,
                props: {
                    imgUrl: persona.avatarUrl,
                    persona,
                    counter: chat ? chat.importantCounter : undefined,
                },
            };
        }
        return {
            Component: DiscussCommand,
            action: () => {
                this.dialog.add(CreateThreadDialog, { name: this.options.searchValue });
            },
            name: _t("Create a new conversation"),
            className: "d-flex justify-content-center",
            props: { icon: "fa fa-fw fa-pencil", isAction: true },
        };
    }
}

commandProviderRegistry.add("find_or_start_conversation", {
    namespace: "@",
    async provide(env, options) {
        const palette = new DiscussCommandPalette(env, options);
        await palette.fetch();
        palette.buildResults();
        palette.commands.slice(0, 8);
        if (!palette.store.inPublicPage) {
            palette.commands.push(palette.makeDiscussCommand("NEW"));
        }
        return palette.commands;
    },
});
