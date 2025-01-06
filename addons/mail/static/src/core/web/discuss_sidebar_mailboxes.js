import { ThreadIcon } from "@mail/core/common/thread_icon";
import { discussSidebarItemsRegistry } from "@mail/core/public_web/discuss_sidebar";

import { Component } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { markEventHandled } from "@web/core/utils/misc";

export class Mailbox extends Component {
    static template = "mail.Mailbox";
    static props = ["mailbox"];
    static components = { ThreadIcon };

    setup() {
        super.setup();
        this.store = useService("mail.store");
    }

    /** @returns {import("models").Thread} */
    get mailbox() {
        return this.props.mailbox;
    }

    /** @param {MouseEvent} ev */
    openThread(ev) {
        markEventHandled(ev, "sidebar.openThread");
        this.mailbox.setAsDiscussThread();
    }
}

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebarMailboxes extends Component {
    static template = "mail.DiscussSidebarMailboxes";
    static props = {};
    static components = { Mailbox };

    setup() {
        super.setup();
        this.store = useService("mail.store");
    }
}

discussSidebarItemsRegistry.add("mailbox", DiscussSidebarMailboxes, { sequence: 20 });
