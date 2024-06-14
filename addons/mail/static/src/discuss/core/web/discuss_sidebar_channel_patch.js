import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { DiscussSidebarChannel } from "@mail/discuss/core/public_web/discuss_sidebar_channel";

/**
 * @type {import("@mail/discuss/core/public_web/discuss_sidebar_channel").DiscussSidebarChannel}
 */
const DiscussSidebarChannelPatch = {
    setup() {
        super.setup(...arguments);
        this.actionService = useService("action");
    },
    openSettings() {
        if (this.props.thread.channel_type === "channel") {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: "discuss.channel",
                res_id: this.props.thread.id,
                views: [[false, "form"]],
                target: "current",
            });
        }
    },
};
patch(DiscussSidebarChannel.prototype, DiscussSidebarChannelPatch);
