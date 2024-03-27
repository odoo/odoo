import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { DiscussCallSettings } from "@mail/discuss/core/common/discuss_call_settings";
import { DiscussNotificationSettings } from "@mail/discuss/core/common/discuss_notification_settings";

export class SettingsMenu extends Component {
    static components = { ActionPanel, DiscussCallSettings, DiscussNotificationSettings };
    static template = "discuss.SettingsMenu";
    static props = ["*"];
    setup() {
        this.state = useState({
            isOnCallSettings: true,
        });
    }

    get title() {
        return _t("Settings");
    }
}
