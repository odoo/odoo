import { onExternalClick } from "@mail/utils/common/hooks";
import { Component } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";

import { useAutofocus, useService } from "@web/core/utils/hooks";

export class MessagingMenuQuickSearch extends Component {
    static components = {};
    static props = ["onClose"];
    static template = "mail.MessagingMenuQuickSearch";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        useAutofocus();
        onExternalClick("search", () => this.props.onClose());
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
