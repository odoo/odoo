import { discussSidebarItemsRegistry } from "@mail/core/web/discuss_sidebar";

import { useService } from "@web/core/utils/hooks";

import { Component, useState } from "@odoo/owl";

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebarStartMeeting extends Component {
    static template = "mail.DiscussSidebarStartMeeting";
    static props = {};
    static components = {};

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
    }

    async onClickStartMeeting() {
        this.store.startMeeting();
    }
}

discussSidebarItemsRegistry.add("start-meeting", DiscussSidebarStartMeeting, { sequence: 10 });
