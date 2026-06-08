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
            Object.values(store["im_livechat.channel"].records)
                .filter((c) => c.channel_ids.length > 0)
                .map((c) => c.id)
        );
        // Show live chat channels with ongoing conversations first
        return Object.values(store["im_livechat.channel"].records)
            .sort((c1, c2) => {
                const c1IsActive = activeChannels.has(c1.id);
                const c2IsActive = activeChannels.has(c2.id);
                if (c1IsActive && !c2IsActive) {
                    return -1;
                }
                if (!c1IsActive && c2IsActive) {
                    return 1;
                }
                return c1.id - c2.id;
            })
            .map((c) => ({
                action: c.are_you_inside ? c.leave.bind(c) : c.join.bind(c),
                Component: LivechatChannelCommand,
                name: c.are_you_inside ? c.leaveTitle : c.joinTitle,
                props: {
                    iconClass: c.are_you_inside
                        ? "fa fa-sign-out text-danger"
                        : "fa fa-sign-in text-success",
                },
            }));
    },
});
