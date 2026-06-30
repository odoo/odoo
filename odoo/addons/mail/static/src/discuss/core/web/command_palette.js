/* @odoo-module */

import { cleanTerm } from "@mail/utils/common/format";

import { Component } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { url } from "@web/core/utils/urls";
import { imageCacheKey } from "@web/views/fields/image/image_field";
import { ImStatus } from "@mail/core/common/im_status";

const commandSetupRegistry = registry.category("command_setup");
const commandProviderRegistry = registry.category("command_provider");

class DiscussCommand extends Component {
    static components = { ImStatus };
    static template = "mail.DiscussCommand";
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
        const messaging = env.services["mail.messaging"];
        const threadService = env.services["mail.thread"];
        const suggestionService = env.services["mail.suggestion"];
        const commands = [];
        const mentionedChannels = threadService.getNeedactionChannels();
        // We don't want to display the same channel twice in the command palette.
        const displayedPartnerIds = new Set();
        if (!options.searchValue) {
            mentionedChannels.slice(0, 3).map((channel) => {
                if (channel.type === "chat") {
                    displayedPartnerIds.add(channel.chatPartner.id);
                }
                commands.push({
                    Component: DiscussCommand,
                    async action() {
                        switch (channel.type) {
                            case "chat":
                                threadService.openChat({ partnerId: channel.chatPartner.id });
                                break;
                            case "group":
                                threadService.open(channel);
                                break;
                            case "channel": {
                                await threadService.joinChannel(channel.id, channel.name);
                                threadService.open(channel);
                            }
                        }
                    },
                    name: channel.displayName,
                    category: "discuss_mentioned",
                    props: {
                        imgUrl: channel.imgUrl,
                        persona: channel.type === "chat" ? channel.correspondent : undefined,
                        counter: threadService.getCounter(channel),
                    },
                });
            });
        }
        const searchResults = await messaging.searchPartners(options.searchValue);
        suggestionService
            .sortPartnerSuggestions(searchResults, options.searchValue)
            .filter((partner) => !displayedPartnerIds.has(partner.id))
            .map((partner) => {
                const chat = threadService.searchChat(partner);
                commands.push({
                    Component: DiscussCommand,
                    action() {
                        threadService.openChat({ partnerId: partner.id });
                    },
                    name: partner.name,
                    props: {
                        imgUrl: threadService.avatarUrl(partner),
                        persona: partner,
                        counter: chat ? threadService.getCounter(chat) : undefined,
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
        const messaging = env.services["mail.messaging"];
        const threadService = env.services["mail.thread"];
        const commands = [];
        const recentChannels = threadService.getRecentChannels();
        // We don't want to display the same thread twice in the command palette.
        const shownChannels = new Set();
        if (!options.searchValue) {
            recentChannels
                .filter((channel) => ["channel", "group"].includes(channel.type))
                .slice(0, 3)
                .map((channel) => {
                    shownChannels.add(channel.id);
                    commands.push({
                        Component: DiscussCommand,
                        async action() {
                            await threadService.joinChannel(channel.id, channel.name);
                            threadService.open(channel);
                        },
                        name: channel.displayName,
                        category: "discuss_recent",
                        props: {
                            imgUrl: channel.imgUrl,
                            counter: threadService.getCounter(channel),
                        },
                    });
                });
        }
        const domain = [
            ["channel_type", "=", "channel"],
            ["name", "ilike", cleanTerm(options.searchValue)],
        ];
        const channelsData = await messaging.orm.searchRead(
            "discuss.channel",
            domain,
            ["channel_type", "name", "avatar_128"],
            { limit: 10 }
        );
        channelsData
            .filter((data) => !shownChannels.has(data.id))
            .map((data) => {
                commands.push({
                    Component: DiscussCommand,
                    async action() {
                        const channel = await threadService.joinChannel(data.id, data.name);
                        threadService.open(channel);
                    },
                    name: data.name,
                    props: {
                        imgUrl: url("/web/image", {
                            model: "discuss.channel",
                            field: "avatar_128",
                            id: data.id,
                            unique: imageCacheKey(data.avatar_128),
                        }),
                    },
                });
            });
        const groups = recentChannels.filter(
            (channel) =>
                !shownChannels.has(channel.id) &&
                channel.type === "group" &&
                cleanTerm(channel.displayName).includes(cleanTerm(options.searchValue))
        );
        groups.map((channel) => {
            commands.push({
                Component: DiscussCommand,
                async action() {
                    threadService.open(channel);
                },
                name: channel.displayName,
                props: {
                    imgUrl: channel.imgUrl,
                    counter: threadService.getCounter(channel),
                },
            });
        });
        return commands;
    },
});
