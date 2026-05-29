import { onExternalClick } from "@mail/utils/common/hooks";
import { Component, onMounted, signal } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";

import { useService } from "@web/core/utils/hooks";

export class MessagingMenuQuickSearch extends Component {
    static components = {};
    static props = ["onClose"];
    static template = "mail.MessagingMenuQuickSearch";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.searchRef = signal();
        this.autofocusRef = signal();
        onMounted(() => this.autofocusRef()?.focus());
        onExternalClick(this.searchRef, () => this.props.onClose());
    }

    onKeydownInput(ev) {
        const hotkey = getActiveHotkey(ev);
        if (hotkey === "escape") {
            ev.stopPropagation();
            ev.preventDefault();
            this.props.onClose();
        }
    }
}
