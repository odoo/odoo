/** @odoo-module */

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const { Component, xml } = owl;

class DialogCommand extends Component {}
DialogCommand.template = xml`
    <div class="o_command_default d-flex align-items-center justify-content-between px-4 py-2 cursor-pointer">
        <t t-slot="name"/>
        <span t-if="props.email" t-out="props.email"/>
    </div>
`;

const commandSetupRegistry = registry.category("command_setup");
commandSetupRegistry.add("@", {
    debounceDelay: 200,
    emptyMessage: _lt("No user found"),
    name: _lt("users"),
    placeholder: _lt("Search for a user..."),
});
commandSetupRegistry.add("#", {
    debounceDelay: 200,
    emptyMessage: _lt("No channel found"),
    name: _lt("channels"),
    placeholder: _lt("Search for a channel..."),
});

const commandProviderRegistry = registry.category("command_provider");
commandProviderRegistry.add("partner", {
    namespace: "@",
    async provide(newEnv, options) {
        const messaging = await newEnv.services.messaging.get();
        const suggestions = [];
        await messaging.models['Partner'].imSearch({
            callback(partners) {
                partners.forEach((partner) => {
                    suggestions.push({
                        Component: DialogCommand,
                        action() {
                            partner.openChat();
                        },
                        name: partner.nameOrDisplayName,
                        props: {
                            email: partner.email,
                        },
                    });
                });
            },
            keyword: options.searchValue,
            limit: 10,
        });
        return suggestions;
    },
});

commandProviderRegistry.add("channel", {
    namespace: "#",
    async provide(newEnv, options) {
        const messaging = await newEnv.services.messaging.get();
        const channels = await messaging.models['Thread'].searchChannelsToOpen({
            limit: 10,
            searchTerm: options.searchValue,
        });
        return channels.map((channel) => ({
            async action() {
                await channel.join();
                // Channel must be pinned immediately to be able to open it before
                // the result of join is received on the bus.
                channel.update({ isServerPinned: true });
                channel.open();
            },
            name: channel.displayName,
        }));
    },
});
