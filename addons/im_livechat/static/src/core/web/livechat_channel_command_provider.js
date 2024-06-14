import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";

class LivechatChannelCommand extends Component {
    static template = "im_livechat.LivechatChannelCommand";
    static props = {
        executeCommand: Function,
        iconClass: String,
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
        if (!store?.has_access_livechat) {
            return [];
        }
        await store.livechatChannels.fetch();
        const activeChannels = new Set(
            Object.values(store.LivechatChannel.records)
                .filter((c) => c.threads.length > 0)
                .map((c) => c.id)
        );
        // Show live chat channels with ongoing conversations first
        return Object.values(store.LivechatChannel.records)
            .sort((c) => (activeChannels.has(c.id) ? -1 : 1))
            .map((c) => ({
                action: c.hasSelfAsMember ? c.leave.bind(c) : c.join.bind(c),
                Component: LivechatChannelCommand,
                name: c.hasSelfAsMember ? c.leaveTitle : c.joinTitle,
                props: {
                    iconClass: c.hasSelfAsMember
                        ? "fa fa-sign-out text-danger"
                        : "fa fa-sign-in text-success",
                },
            }));
    },
});
