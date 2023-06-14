/* @odoo-module */

import { createGroupChat } from "@mail/core/common/thread_service";
import { Sidebar } from "@mail/core/web/sidebar";
import { useRtc } from "@mail/discuss/call/common/rtc_hook";

import { patch } from "@web/core/utils/patch";

patch(Sidebar.prototype, "discuss/call/web", {
    setup() {
        this._super(...arguments);
        this.rtc = useRtc();
    },
    async onClickStartMeeting() {
        const thread = await createGroupChat({
            default_display_mode: "video_full_screen",
            partners_to: [this.store.self.id],
        });
        await this.rtc.toggleCall(thread, { video: true });
    },
});
