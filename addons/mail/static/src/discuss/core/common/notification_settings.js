import { Component, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";

export class NotificationSettings extends Component {
    static components = { Dropdown, DropdownItem };
    static props = ["hasSizeConstraints?", "thread", "close", "className?"];
    static template = "discuss.NotificationSettings";

    setup() {
        this.store = useState(useService("mail.store"));
    }

    selectUnmute() {
        this.props.thread.mute();
        this.props.close();
    }

    setMute(minutes) {
        this.props.thread.mute({ minutes });
        this.props.close();
    }
}
