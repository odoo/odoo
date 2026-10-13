import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class MessageLayoutDropdown extends Component {
    static components = { Dropdown, DropdownItem };
    static template = "mail.MessageLayoutDropdown";

    setup() {
        this.store = useService("mail.store");
        this.uiService = useService("ui");
        this.layouts = [
            { code: "bubble", icon: "forum", name: _t("Bubble Layout") },
            { code: "compact", icon: "reorder", name: _t("Compact Layout") },
        ];
    }

    get currentLayout() {
        return (
            this.layouts.find((layout) => layout.code === this.store.settings.messageLayout) ||
            this.layouts[0]
        );
    }

    setMessageLayout(code) {
        this.store.settings.messageLayout = code;
    }
}

export function messageLayoutItem(env) {
    return {
        type: "component",
        contentComponent: MessageLayoutDropdown,
        sequence: 46,
    };
}

registry.category("user_menuitems").add("message_layout", messageLayoutItem);
