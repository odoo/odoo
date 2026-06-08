import { useRef } from "@web/owl2/utils";
import { ThreadIcon } from "@mail/core/common/thread_icon";
import { discussSidebarItemsRegistry } from "@mail/core/public_web/discuss_app/sidebar/sidebar";
import { useHover } from "@mail/utils/common/hooks";

import { Component, props, types } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

import { useService } from "@web/core/utils/hooks";
import { markEventHandled } from "@web/core/utils/misc";

export class Mailbox extends Component {
    static template = "mail.Mailbox";
    static components = { Dropdown, ThreadIcon };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = props({ mailbox: types.instanceOf(this.store["mail.thread"].Class) });
        this.hover = useHover(["root", "floating"], {
            onHover: () => {
                if (this.store.discuss.isSidebarCompact) {
                    this.floating.isOpen = true;
                }
            },
            onAway: () => {
                if (this.store.discuss.isSidebarCompact) {
                    this.floating.isOpen = false;
                }
            },
        });
        this.floating = useDropdownState();
        this.rootRef = useRef("root");
    }

    /** @returns {import("models").Thread} */
    get mailbox() {
        return this.props.mailbox;
    }

    /** @param {MouseEvent} ev */
    openThread(ev) {
        markEventHandled(ev, "sidebar.openChannel");
        this.mailbox.setAsDiscussThread();
    }
}

export class DiscussSidebarMailboxes extends Component {
    static template = "mail.DiscussSidebarMailboxes";
    static components = { Mailbox };

    setup() {
        super.setup();
        this.store = useService("mail.store");
    }
}

discussSidebarItemsRegistry.add("mailbox", DiscussSidebarMailboxes, { sequence: 20 });
