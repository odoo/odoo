/* @odoo-module */

import { cleanTerm } from "@mail/utils/common/format";

import { Component, xml } from "@odoo/owl";

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const commandSetupRegistry = registry.category("command_setup");
const commandProviderRegistry = registry.category("command_provider");

// -----------------------------------------------------------------------------
// add @ namespace + provider
// -----------------------------------------------------------------------------
commandSetupRegistry.add("@", {
    debounceDelay: 200,
    emptyMessage: _lt("No user found"),
    name: _lt("users"),
    placeholder: _lt("Search for a user..."),
});

class DialogCommand extends Component {}
DialogCommand.template = xml`
    <div class="o_command_default d-flex align-items-center justify-content-between px-4 py-2 cursor-pointer">
        <t t-slot="name"/>
        <span t-if="props.email" t-out="props.email"/>
    </div>
`;

commandProviderRegistry.add("mail.partner", {
    namespace: "@",
    async provide(env, options) {
        /** @type {import("@mail/core/common/messaging_service").Messaging} */
        const messaging = env.services["mail.messaging"];
        const threadService = env.services["mail.thread"];
        /** @type {import("@mail/core/common/suggestion_service").SuggestionService} */
        const suggestionService = env.services["mail.suggestion"];
        const results = await messaging.searchPartners(options.searchValue);
        return suggestionService
            .sortPartnerSuggestions(results, options.searchValue)
            .map(function (partner) {
                return {
                    Component: DialogCommand,
                    action() {
                        threadService.openChat({ partnerId: partner.id });
                    },
                    name: partner.name,
                    props: { email: partner.email },
                };
            });
    },
});

// -----------------------------------------------------------------------------
// add # namespace + provider
// -----------------------------------------------------------------------------

commandSetupRegistry.add("#", {
    debounceDelay: 200,
    emptyMessage: _lt("No channel found"),
    name: _lt("channels"),
    placeholder: _lt("Search for a channel..."),
});

commandProviderRegistry.add("discuss.channel", {
    namespace: "#",
    async provide(env, options) {
        /** @type {import("@mail/core/common/messaging_service").Messaging} */
        const messaging = env.services["mail.messaging"];
        const threadService = env.services["mail.thread"];
        const domain = [
            ["channel_type", "=", "channel"],
            ["name", "ilike", cleanTerm(options.searchValue)],
        ];
        const channelsData = await messaging.orm.searchRead(
            "discuss.channel",
            domain,
            ["channel_type", "name"],
            { limit: 10 }
        );
        return channelsData.map((data) => ({
            async action() {
                const channel = await threadService.joinChannel(data.id, data.name);
                threadService.open(channel);
            },
            // todo: handle displayname in a way (seems like "group" channels
            // do not have a name
            name: data.name,
        }));
    },
});
