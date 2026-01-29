import { ThreadIcon } from "@mail/core/common/thread_icon";
import { discussSidebarItemsRegistry } from "@mail/core/public_web/discuss_app/sidebar/sidebar";
import { useHover } from "@mail/utils/common/hooks";

import { Component, useRef } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { markEventHandled } from "@web/core/utils/misc";

export class Mailbox extends Component {
    static template = "mail.Mailbox";
    static props = [];
    static components = { Dropdown, ThreadIcon };

    setup() {
        super.setup();
        this.store = useService("mail.store");
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
        return this.store.self_user?.notification_type === "inbox"
            ? this.store.inbox
            : this.store.starred;
    }

    get mailboxName() {
        return this.store.self_user?.notification_type === "inbox"
            ? _t("Inbox")
            : _t("Starred messages");
    }

    /** @param {MouseEvent} ev */
    openThread(ev) {
        markEventHandled(ev, "sidebar.openChannel");
        this.mailbox.setAsDiscussThread();
    }
}

discussSidebarItemsRegistry.add("mailbox", Mailbox, { sequence: 20 });
