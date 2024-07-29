import { discussSidebarItemsRegistry } from "@mail/core/public_web/discuss_sidebar";

import { Component, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { DiscussSidebarMailbox } from "./discuss_sidebar_mailbox";

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebarMailboxes extends Component {
    static template = "mail.DiscussSidebarMailboxes";
    static props = {};
    static components = { DiscussSidebarMailbox };

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
    }
}

discussSidebarItemsRegistry.add("mailbox", DiscussSidebarMailboxes, { sequence: 20 });
