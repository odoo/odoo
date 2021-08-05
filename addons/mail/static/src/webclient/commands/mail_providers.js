/** @odoo-module */

import { cleanSearchTerm } from "@mail/utils/utils";
import { registry } from "@web/core/registry";
import { fuzzyLookup } from "@web/core/utils/search";

// TODO LEGACY ENV
import env from "web.env";

const { Component } = owl;
const { xml } = owl.tags;

class DialogCommand extends Component {}
DialogCommand.template = xml`
    <t t-name="web.dialogCommand" owl="1">
        <div class="o_command_default o_command_dialog">
            <span t-esc="props.name" />
            <span t-if="props.email" t-esc="props.email" />
        </div>
    </t>`;

const commandProviderRegistry = registry.category("command_provider");

commandProviderRegistry.add("partner", {
    nameSpace: "@",
    provide: async (newEnv, options) => {
        const suggestions = [];
        let partners = env.models["mail.partner"].searchChatsToOpen(options.searchValue, 10);
        if (!partners.length) {
            await env.models["mail.partner"].fetchChatsToOpen(options.searchValue, 10);
            partners = env.models["mail.partner"].searchChatsToOpen(options.searchValue, 10);
        }
        partners.forEach((partner) => {
            suggestions.push({
                name: partner.nameOrDisplayName,
                email: partner.email,
                Component: DialogCommand,
                action: () => {
                    partner.openChat();
                },
            });
        });

        return suggestions;
    },
});

commandProviderRegistry.add("channel", {
    nameSpace: "#",
    provide: async (newEnv, options) => {
        const suggestions = [];
        let threads = env.models["mail.thread"].searchChannelsToOpen(options.searchValue, 10);
        if (!threads.length) {
            await env.models["mail.thread"].fetchChannelsToOpen(options.searchValue, 10);
            threads = env.models["mail.thread"].searchChannelsToOpen(options.searchValue, 10);
        }
        threads.forEach((thread) => {
            suggestions.push({
                name: thread.displayName,
                action: async () => {
                    await thread.join();
                    // Channel must be pinned immediately to be able to open it before
                    // the result of join is received on the bus.
                    thread.update({ isServerPinned: true });
                    thread.open();
                },
            });
        });

        return suggestions;
    },
});
