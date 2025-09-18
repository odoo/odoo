import { onExternalClick } from "@mail/utils/common/hooks";
import { Component } from "@odoo/owl";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { getActiveHotkey } from "@web/services/hotkeys/hotkey_service";
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
