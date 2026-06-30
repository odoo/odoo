import { DiscussAvatar } from "@mail/core/common/discuss_avatar";
import { MessagingMenu } from "@mail/core/public_web/messaging_menu/messaging_menu";
import { useDiscussSystray } from "@mail/utils/common/hooks";
import { incrementFn } from "@mail/utils/common/signal";

import { Component, computed, signal, useEffect } from "@odoo/owl";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class MessagingMenuInDropdown extends Component {
    static components = { DiscussAvatar, MessagingMenu, Dropdown };
    static template = "mail.MessagingMenuInDropdown";

    setup() {
        super.setup();
        this.discussSystray = useDiscussSystray();
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.dropdown = useDropdownState();
        this.menuState = computed(() => this.store.messagingMenuSystrayState);
        // Bound once so `close` is a stable (props.static) handler.
        this.closeDropdown = this.dropdown.close.bind(this.dropdown);
        this.searchInputAutofocus = signal(0);
        this.triggerSearchInputAutofocus = incrementFn(this.searchInputAutofocus);
        useEffect(() => {
            if (!this.dropdown.isOpen) {
                return;
            }
            void this.store.messagingMenuSystrayState.activeTab;
            void this.store.messagingMenuSystrayState.selectedFilter;
            this.triggerSearchInputAutofocus();
        });
    }
}

registry
    .category("systray")
    .add("mail.messaging_menu", { Component: MessagingMenuInDropdown }, { sequence: 25 });
