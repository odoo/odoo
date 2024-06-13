import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";

import { DiscussNotificationSettings } from "@mail/discuss/core/common/discuss_notification_settings";

export class DiscussNotificationSettingsClientAction extends Component {
    static components = { DiscussNotificationSettings };
    static props = ["*"];
    static template = "mail.DiscussNotificationSettingsClientAction";
}

registry
    .category("actions")
    .add("mail.discuss_notification_settings_action", DiscussNotificationSettingsClientAction);
