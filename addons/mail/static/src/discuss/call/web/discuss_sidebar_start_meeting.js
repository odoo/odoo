/* @odoo-module */

import { useStore } from "@mail/core/common/messaging_hook";
import { discussSidebarItemsRegistry } from "@mail/core/web/discuss_sidebar";
import { useRtc } from "@mail/discuss/call/common/rtc_hook";
import { useDiscussCoreCommon } from "@mail/discuss/core/common/discuss_core_common_service";

import { Component } from "@odoo/owl";

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebarStartMeeting extends Component {
    static template = "mail.DiscussSidebarStartMeeting";
    static props = {};
    static components = {};

    setup() {
        this.discussCoreCommonService = useDiscussCoreCommon();
        this.rtc = useRtc();
        this.store = useStore();
    }

    async onClickStartMeeting() {
        const thread = await this.discussCoreCommonService.createGroupChat({
            default_display_mode: "video_full_screen",
            partners_to: [this.store.self.id],
        });
        this.rtc.toggleCall(thread, { video: true });
        this.env.onStartMeeting?.();
    }
}

discussSidebarItemsRegistry.add("start-meeting", DiscussSidebarStartMeeting, { sequence: 10 });
