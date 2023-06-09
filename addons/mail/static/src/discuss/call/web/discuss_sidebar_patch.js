/* @odoo-module */

import { Sidebar } from "@mail/core/web/sidebar";
import { useRtc } from "@mail/discuss/call/common/rtc_hook";

import { patch } from "@web/core/utils/patch";

Sidebar.props = [...Sidebar.props, "onStartMeeting?"];

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
        await this.props.onStartMeeting?.();
    },
});
