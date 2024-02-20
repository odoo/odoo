/* @odoo-module */

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { LivechatChannel } from "@im_livechat/core/web/livechat_channel_model";

class LivechatChannelCommand extends Component {
    static template = "im_livechat.LivechatChannelCommand";
    static props = {
        channel: LivechatChannel,
        executeCommand: Function,
        name: String,
        searchValue: String,
        slots: Object,
    };
}

registry.category("command_provider").add("im_livechat.channel_join_leave", {
    /**
     * @param {import("@web/env").OdooEnv} env
     */
    async provide(env) {
        const store = env.services["mail.store"];
        if (!store?.self.hasLivechatAccess) {
            return [];
        }
        await store.livechatChannels.fetch();
        const activeChannels = new Set(
            Object.values(store.LivechatChannel.records)
                .filter((c) => c.discussChannels.length > 0)
                .map((c) => c.id)
        );
        // Show live chat channels with ongoing conversations first
        return Object.values(store.LivechatChannel.records)
            .sort((c) => (activeChannels.has(c.id) ? -1 : 1))
            .map((c) => ({
                async action() {
                    if (c.hasSelfAsMember) {
                        await c.leave();
                    } else {
                        await c.join();
                    }
                },
                Component: LivechatChannelCommand,
                name: c.name,
                props: { channel: c },
            }));
    },
});
