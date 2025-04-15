/* @odoo-module */

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
        this.store = useState(useService("mail.store"));
        this.threadService = useState(useService("mail.thread"));
    }

    /**
     * @param {MouseEvent} ev
     * @param {import("models").Thread} thread
     */
    openThread(ev, thread) {
        markEventHandled(ev, "sidebar.openThread");
        this.threadService.setDiscussThread(thread);
    }
}

discussSidebarItemsRegistry.add("mailbox", DiscussSidebarMailboxes, { sequence: 20 });
