import { ThreadIcon } from "@mail/core/common/thread_icon";
<<<<<<< e3f8e4ecbd9b96602c9d9a961d31d124d52cc8f5:addons/mail/static/src/core/web/discuss_app/sidebar/mailboxes.js
import { discussSidebarItemsRegistry } from "@mail/core/public_web/discuss_app/sidebar/sidebar";
import { useHover } from "@mail/utils/common/hooks";
||||||| b865fb3e4fce8f0432e3a8fee8e6b812c1f68940:addons/mail/static/src/core/web/discuss_sidebar_mailboxes.js
import { discussSidebarItemsRegistry } from "@mail/core/public_web/discuss_sidebar";
import { useHover } from "@mail/utils/common/hooks";
=======
import { discussSidebarItemsRegistry } from "@mail/core/public_web/discuss_sidebar";
import { useHover, UseHoverOverlay } from "@mail/utils/common/hooks";
>>>>>>> a78bf6995fa7fb9b580ce67aa5163e931accde0b:addons/mail/static/src/core/web/discuss_sidebar_mailboxes.js

import { Component, useRef } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

import { useService } from "@web/core/utils/hooks";
import { markEventHandled } from "@web/core/utils/misc";

export class Mailbox extends Component {
    static template = "mail.Mailbox";
    static props = ["mailbox"];
    static components = { Dropdown, ThreadIcon, UseHoverOverlay };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.hover = useHover(["root"], {
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
