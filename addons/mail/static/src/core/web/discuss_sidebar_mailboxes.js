import { ThreadIcon } from "@mail/core/common/thread_icon";
import { discussSidebarItemsRegistry } from "@mail/core/web/discuss_sidebar";

import { Component, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { markEventHandled } from "@web/core/utils/misc";

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebarMailboxes extends Component {
    static template = "mail.DiscussSidebarMailboxes";
    static props = {};
    static components = { ThreadIcon };

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
    }

    /**
     * @param {MouseEvent} ev
     * @param {import("models").Thread} thread
     */
    openThread(ev, thread) {
        markEventHandled(ev, "sidebar.openThread");
        thread.setAsDiscussThread();
    }
}

discussSidebarItemsRegistry.add("mailbox", DiscussSidebarMailboxes, { sequence: 20 });
