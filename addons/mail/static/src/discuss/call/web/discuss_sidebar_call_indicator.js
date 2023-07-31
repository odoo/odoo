/* @odoo-module */

import { Thread } from "@mail/core/common/thread_model";
import { useRtc } from "@mail/discuss/call/common/rtc_hook";
import { discussSidebarChannelIndicatorsRegistry } from "@mail/discuss/core/web/discuss_sidebar_categories";

import { Component } from "@odoo/owl";

/**
 * @typedef {Object} Props
 * @property {import("@mail/core/common/thread_model").Thread} thread
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebarCallIndicator extends Component {
    static template = "mail.DiscussSidebarCallIndicator";
    static props = { thread: { type: Thread } };
    static components = {};

    setup() {
        this.rtc = useRtc();
    }
}

discussSidebarChannelIndicatorsRegistry.add("call-indicator", DiscussSidebarCallIndicator);
