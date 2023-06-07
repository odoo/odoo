/* @odoo-module */

import { useRtc } from "@mail/discuss/call/rtc_hook";
import { Sidebar } from "@mail/web/discuss_app/sidebar";
import { patch } from "@web/core/utils/patch";

patch(Sidebar.prototype, "discuss/call/web", {
    setup() {
        this._super(...arguments);
        this.rtc = useRtc();
    },
    async onClickStartMeeting() {
        const thread = await this.threadService.createGroupChat({
            default_display_mode: "video_full_screen",
            partners_to: [this.store.self.id],
        });
        await this.rtc.toggleCall(thread, { video: true });
    },
});
