import { Component, computed, signal, t, useProps } from "@odoo/owl";

import { location } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useAutofocus, useService } from "@web/core/utils/hooks";

/**
 * Equivalent of the web client user menu on the public page: guests can change their
 * name there, and everyone can pick the color scheme when it is supported. The compact
 * version only shows the avatar, for the chat window header on small screens.
 */
export class PublicSelfMenu extends Component {
    static components = { Dropdown, DropdownItem };
    static template = "mail.PublicSelfMenu";

    guestNameRef = signal.ref();

    setup() {
        super.setup();
        this.props = useProps({ compact: t.boolean().optional() });
        this.store = useService("mail.store");
        useAutofocus({ ref: this.guestNameRef });
    }

    hasMenu = computed(() => this.isGuest() || Boolean(this.store.publicColorScheme));

    // `self_guest` has a dummy default for logged-in users.
    isGuest = computed(() => Boolean(this.store.self_guest && !this.store.self_user));

    /** @param {KeyboardEvent} ev */
    onKeydownGuestName(ev) {
        switch (ev.key) {
            case "Enter":
                // Prevent the dropdown navigation from selecting its active item.
                ev.stopPropagation();
                ev.target.blur();
                break;
            case "Escape":
                ev.target.value = this.store.self_guest.name;
                break;
        }
    }

    /** @param {string} name */
    async renameGuest(name) {
        const newName = name.trim();
        if (newName && this.store.self_guest.name !== newName) {
            await this.store.self_guest.updateGuestName(newName);
        }
    }

    /** @param {"light"|"dark"} colorScheme */
    setColorScheme(colorScheme) {
        if (colorScheme === this.store.publicColorScheme) {
            return;
        }
        // Same cookie as the web client, the server picks the assets from it.
        cookie.set("color_scheme", colorScheme);
        location.reload();
    }
}
