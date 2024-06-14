import { Component, useEffect, useRef, useState } from "@odoo/owl";

import { ThreadIcon } from "@mail/core/common/thread_icon";

import { useService } from "@web/core/utils/hooks";
import { markEventHandled } from "@web/core/utils/misc";

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebarMailbox extends Component {
    static template = "mail.DiscussSidebarMailbox";
    static props = ["mailbox"];
    static components = { ThreadIcon };

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.root = useRef("root");
        useEffect(
            () => {
                if (this.props.mailbox.eq(this.store.discuss.thread)) {
                    this.env.discussSidebar.setActiveRef(this.root);
                }
            },
            () => [this.store.discuss.thread]
        );
    }

    /** @param {MouseEvent} ev */
    openThread(ev) {
        markEventHandled(ev, "sidebar.openThread");
        this.props.mailbox.setAsDiscussThread();
    }
}
