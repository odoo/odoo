import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";

export class NotificationSettings extends Component {
    static components = { Dropdown, DropdownItem };
    static props = ["hasSizeConstraints?", "thread", "close", "className?"];
    static template = "discuss.NotificationSettings";

    get muteUntilText() {
        if (
            this.props.thread.mute_until_dt &&
            this.props.thread.mute_until_dt.year <= new Date().getFullYear() + 2
        ) {
            return _t("Until ") + this.props.thread.mute_until_dt.toFormat("MM/dd, HH:mm");
        }
        // Forever is a special case, so we don't want to display the date.
        return undefined;
    }

    selectUnmute() {
        this.props.thread.mute();
        this.props.close();
    }

    setMute(minutes) {
        this.props.thread.mute({ minutes });
        this.props.close();
    }

    setSetting(setting) {
        this.props.thread.updateCustomNotifications(setting.id);
    }
}
