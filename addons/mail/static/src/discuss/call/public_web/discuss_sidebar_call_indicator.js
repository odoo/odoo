import { Thread } from "@mail/core/common/thread_model";
import { discussSidebarChannelIndicatorsRegistry } from "@mail/discuss/core/public_web/discuss_sidebar_categories";
import { useHover } from "@mail/utils/common/hooks";

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {import(models").Thread} thread
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebarCallIndicator extends Component {
    static template = "mail.DiscussSidebarCallIndicator";
    static props = { thread: { type: Thread } };
    static components = {};

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.rtc = useState(useService("discuss.rtc"));
        this.hover = useHover("root");
    }

    onClick() {
        if (this.store.discuss.isSidebarCompact) {
            return;
        }
        if (this.props.thread.eq(this.rtc.state.channel)) {
            this.rtc.leaveCall(this.props.thread);
        } else {
            this.rtc.joinCall(this.props.thread);
        }
    }
}

discussSidebarChannelIndicatorsRegistry.add("call-indicator", DiscussSidebarCallIndicator);
