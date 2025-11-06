import { DiscussSidebarChannel } from "@mail/discuss/core/public_web/discuss_app/sidebar/channel";
import { patch } from "@web/core/utils/patch";

patch(DiscussSidebarChannel.prototype, {
    get showThreadIcon() {
        return this.channel.channel_type === "livechat" || super.showThreadIcon;
    },
});
