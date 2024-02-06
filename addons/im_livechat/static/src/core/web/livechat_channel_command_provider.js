/* @odoo-module */

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";

class LivechatChannelCommand extends Component {
    static template = "im_livechat.LivechatChannelCommand";
    static props = ["channel"];
}

registry.category("command_provider").add("im_livechat.channel_join_leave", {
    /**
     * @param {import("@web/env").OdooEnv} env
     */
    async provide(env) {
        const activeChannels = new Set(
            Object.values(env.services["mail.store"].Thread.records)
                .filter(({ type }) => type === "livechat")
                .map(({ livechat_channel_id }) => livechat_channel_id)
        );
        const matchingChannels = Object.values(env.services["mail.store"].LivechatChannel.records);
        // Show live chat channels for which the user already has ongoing
        // conversations first.
        matchingChannels.sort((a) => (activeChannels.has(a.id) ? -1 : 1));
        return matchingChannels.map((channel) => ({
            async action() {
                if (channel.hasSelfAsMember) {
                    await channel.leave();
                } else {
                    await channel.join();
                }
            },
            Component: LivechatChannelCommand,
            name: channel.name,
            props: { channel },
        }));
    },
});
