/* @odoo-module */

import { Sidebar } from "@mail/web/discuss_app/sidebar";
import { useRtc } from "@mail/discuss/rtc/rtc_hook";
import { createLocalId } from "@mail/utils/misc";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(Sidebar.prototype, "discuss", {
    setup(env, services) {
        this._super(...arguments);
        this.rtc = useRtc();
        this.discussStore = useService("discuss.store");
    },
    async onClickStartMeeting() {
        const thread = await this.threadService.createGroupChat({
            default_display_mode: "video_full_screen",
            partners_to: [this.store.self.id],
        });
        const channel = this.discussStore.channels[createLocalId("discuss.channel", thread.id)];
        await this.rtc.toggleCall(channel, { video: true });
    },
});
