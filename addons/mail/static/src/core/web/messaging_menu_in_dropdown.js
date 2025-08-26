import { DiscussAvatar } from "@mail/core/common/discuss_avatar";
import { MessagingMenu } from "@mail/core/public_web/messaging_menu/messaging_menu";
import { useDiscussSystray, useHover } from "@mail/utils/common/hooks";
import { incrementFn } from "@mail/utils/common/signal";
import { useAncestors } from "@mail/core/common/ancestor_plugin";

import { Component, computed, signal, useEffect } from "@odoo/owl";

import { useCommand } from "@web/core/commands/command_hook";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { getVisibleElements } from "@web/core/utils/ui";

export class MessagingMenuInDropdown extends Component {
    static components = { DiscussAvatar, MessagingMenu, Dropdown };
    static template = "mail.MessagingMenuInDropdown";

    setup() {
        super.setup();
        this.ancestors = useAncestors();
        this.dropdown = useDropdownState();
        this.buttonRef = signal.ref();
        this.discussSystray = useDiscussSystray(this.dropdown);
        this.store = useService("mail.store");
        this.menuState = computed(() => this.store.messagingMenuSystrayState);
        const isHotkeyFree = () =>
            !getVisibleElements(this.store.ui.activeElement(), "[data-hotkey='shift+d' i]").length;
        useCommand(
            _t("Toggle Messaging Menu"),
            () => (this.dropdown.isOpen ? this.dropdown.close() : this.dropdown.open()),
            {
                hotkey: "alt+shift+d",
                hotkeyOptions: {
                    bypassEditableProtection: true,
                    isAvailable: isHotkeyFree,
                    withOverlay: () => isHotkeyFree() && this.buttonRef(),
                },
            }
        );
        // Reading the state creates it, which starts the initial load of the menu content.
        useHover([this.buttonRef], {
            onHover: () => void this.store.messagingMenuSystrayState,
        });
        // Bound once so `close` is a stable (useProps.static) handler.
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
