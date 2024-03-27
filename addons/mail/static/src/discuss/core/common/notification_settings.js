import { useState, Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";

export class NotificationSettings extends Component {
    static components = { Dropdown, DropdownItem };
    static props = ["hasSizeConstraints?", "thread", "close", "className?"];
    static template = "discuss.NotificationSettings";

    setup() {
        this.store = useState(useService("mail.store"));
        this.threadService = useState(useService("mail.thread"));
    }

    selectUnmute() {
        this.threadService.muteThread(this.props.thread);
        this.props.close();
    }

    setMute(minutes) {
        this.threadService.muteThread(this.props.thread, { minutes });
        this.props.close();
    }

    setNotification(id) {
        this.threadService.updateCustomNotifications(this.props.thread, id);
    }
}
