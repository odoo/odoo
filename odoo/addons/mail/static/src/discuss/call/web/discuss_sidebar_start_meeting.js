/* @odoo-module */

import { discussSidebarItemsRegistry } from "@mail/core/web/discuss_sidebar";

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebarStartMeeting extends Component {
    static template = "mail.DiscussSidebarStartMeeting";
    static props = {};
    static components = {};

    setup() {
        this.discussCoreCommonService = useState(useService("discuss.core.common"));
        this.rtc = useState(useService("discuss.rtc"));
        this.store = useState(useService("mail.store"));
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
