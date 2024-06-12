/* @odoo-module */

import { useState, Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class NotificationSettings extends Component {
    static components = { Dropdown, DropdownItem };
    static props = ["hasSizeConstraints?", "thread", "close", "className?"];
    static template = "discuss.NotificationSettings";

    setup() {
        this.threadService = useState(useService("mail.thread"));
    }

    get muteUntilText() {
        if (
            this.props.thread.muteUntilDateTime &&
            this.props.thread.muteUntilDateTime.year <= new Date().getFullYear() + 2
        ) {
            return _t("Until ") + this.props.thread.muteUntilDateTime.toFormat("MM/dd, HH:mm");
        }
        // Forever is a special case, so we don't want to display the date.
        return undefined;
    }

    selectUnmute() {
        this.threadService.muteThread(this.props.thread);
        this.props.close();
    }

    setMute(minutes) {
        this.threadService.muteThread(this.props.thread, { minutes });
        this.props.close();
    }

    setSetting(setting) {
        this.threadService.updateCustomNotifications(this.props.thread, setting.id);
    }
}
