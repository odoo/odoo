/** @odoo-module */

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const { Component } = owl;
const { xml } = owl.tags;

class DialogCommand extends Component {}
DialogCommand.template = xml`
    <div class="o_command_default">
        <span t-esc="props.name"/>
        <span t-if="props.email" t-esc="props.email"/>
    </div>
`;

const commandEmptyMessageRegistry = registry.category("command_empty_list");
commandEmptyMessageRegistry.add("@", _lt("No user found"));
commandEmptyMessageRegistry.add("#", _lt("No channel found"));

const commandProviderRegistry = registry.category("command_provider");
commandProviderRegistry.add("partner", {
    namespace: "@",
    async provide(newEnv, options) {
        const messaging = await Component.env.services.messaging.get();
        const suggestions = [];
        await messaging.models['mail.partner'].imSearch({
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
        const messaging = await Component.env.services.messaging.get();
        const channels = await messaging.models['mail.thread'].searchChannelsToOpen({
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
