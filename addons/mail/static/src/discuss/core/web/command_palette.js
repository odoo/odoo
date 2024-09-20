import { cleanTerm } from "@mail/utils/common/format";

import { Component } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { imageUrl } from "@web/core/utils/urls";
import { ImStatus } from "@mail/core/common/im_status";

const commandSetupRegistry = registry.category("command_setup");
const commandProviderRegistry = registry.category("command_provider");

class DiscussCommand extends Component {
    static components = { ImStatus };
    static template = "mail.DiscussCommand";
    static props = {
        counter: { type: Number, optional: true },
        executeCommand: Function,
        imgUrl: String,
        name: String,
        persona: { type: Object, optional: true },
        channel: { type: Object, optional: true },
        searchValue: String,
        slots: Object,
    };
}

// -----------------------------------------------------------------------------
// add @ namespace + provider
// -----------------------------------------------------------------------------
commandSetupRegistry.add("@", {
    debounceDelay: 200,
    emptyMessage: _t("No user found"),
    name: _t("users"),
    placeholder: _t("Search for a user..."),
});

commandProviderRegistry.add("mail.partner", {
    namespace: "@",
    /**
     * @param {import("@web/env").OdooEnv} env
     */
    async provide(env, options) {
        const store = env.services["mail.store"];
        await store.channels.fetch();
        const suggestionService = env.services["mail.suggestion"];
        const commands = [];
        const mentionedChannels = store.getNeedactionChannels();
        // We don't want to display the same channel twice in the command palette.
        const displayedPartnerIds = new Set();
        if (!options.searchValue) {
            mentionedChannels.slice(0, 3).map((channel) => {
                if (channel.channel_type === "chat") {
                    displayedPartnerIds.add(channel.correspondent.persona.id);
                }
                commands.push({
                    Component: DiscussCommand,
                    async action() {
                        switch (channel.channel_type) {
                            case "chat":
                                store.openChat({ partnerId: channel.correspondent.persona.id });
                                break;
                            case "group":
                                channel.open();
                                break;
                            case "channel": {
                                await store.joinChannel(channel.id, channel.name);
                                channel.open();
                            }
                        }
                    },
                    name: channel.displayName,
                    category: "discuss_mentioned",
                    props: {
                        imgUrl: channel.avatarUrl,
                        persona:
                            channel.channel_type === "chat"
                                ? channel.correspondent.persona
                                : undefined,
                        counter: channel.importantCounter,
                    },
                });
            });
        }
        const searchResults = await store.searchPartners(options.searchValue);
        suggestionService
            .sortPartnerSuggestions(searchResults, options.searchValue)
            .filter((partner) => !displayedPartnerIds.has(partner.id))
            .map((partner) => {
                const chat = partner.searchChat();
                commands.push({
                    Component: DiscussCommand,
                    action() {
                        store.openChat({ partnerId: partner.id });
                    },
                    name: partner.name,
                    props: {
                        imgUrl: partner.avatarUrl,
                        persona: partner,
                        counter: chat ? chat.importantCounter : undefined,
                    },
                });
            });
        return commands;
    },
});

// -----------------------------------------------------------------------------
// add # namespace + provider
// -----------------------------------------------------------------------------

commandSetupRegistry.add("#", {
    debounceDelay: 200,
    emptyMessage: _t("No channel found"),
    name: _t("channels"),
    placeholder: _t("Search for a channel..."),
});

commandProviderRegistry.add("discuss.channel", {
    namespace: "#",
    /**
     * @param {import("@web/env").OdooEnv} env
     */
    async provide(env, options) {
        const store = env.services["mail.store"];
        await store.channels.fetch();
        const commands = [];
        const recentChannels = store.getRecentChannels();
        // We don't want to display the same thread twice in the command palette.
        const shownChannels = new Set();
        if (!options.searchValue) {
            recentChannels
                .filter((channel) => ["channel", "group"].includes(channel.channel_type))
                .slice(0, 3)
                .map((channel) => {
                    shownChannels.add(channel.id);
                    commands.push({
                        Component: DiscussCommand,
                        async action() {
                            await store.joinChannel(channel.id, channel.name);
                            channel.open();
                        },
                        name: channel.displayName,
                        category: "discuss_recent",
                        props: {
                            channel,
                            imgUrl: channel.avatarUrl,
                            counter: channel.importantCounter,
                        },
                    });
                });
        }
        const domain = [
            ["channel_type", "=", "channel"],
            ["name", "ilike", cleanTerm(options.searchValue)],
        ];
        const channelsData = await env.services.orm.searchRead(
            "discuss.channel",
            domain,
            ["channel_type", "name", "avatar_cache_key", "parent_channel_id"],
            { limit: 10 }
        );
        channelsData
            .filter((data) => !shownChannels.has(data.id))
            .map((data) => {
                const channel = store.Thread.insert({
                    ...data,
                    model: "discuss.channel",
                    parent_channel_id: data.parent_channel_id
                        ? {
                              id: data.parent_channel_id[0],
                              model: "discuss.channel",
                              name: data.parent_channel_id[1],
                          }
                        : null,
                });
                commands.push({
                    Component: DiscussCommand,
                    async action() {
                        const channel = await store.joinChannel(data.id, data.name);
                        channel.open();
                    },
                    name: data.name,
                    props: {
                        channel,
                        imgUrl: imageUrl("discuss.channel", data.id, "avatar_128", {
                            unique: data.avatar_cache_key,
                        }),
                    },
                });
            });
        const groups = recentChannels.filter(
            (channel) =>
                !shownChannels.has(channel.id) &&
                channel.channel_type === "group" &&
                cleanTerm(channel.displayName).includes(cleanTerm(options.searchValue))
        );
        groups.map((channel) => {
            commands.push({
                Component: DiscussCommand,
                async action() {
                    channel.open();
                },
                name: channel.displayName,
                props: {
                    imgUrl: channel.avatarUrl,
                    counter: channel.importantCounter,
                },
            });
        });
        return commands;
    },
});
