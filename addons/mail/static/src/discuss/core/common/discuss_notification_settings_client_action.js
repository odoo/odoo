import { Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";

import { DiscussNotificationSettings } from "@mail/discuss/core/common/discuss_notification_settings";

export class DiscussNotificationSettingsClientAction extends Component {
    static components = { DiscussNotificationSettings };
    static props = ["*"];
    static template = xml`
        <div class="o-mail-DiscussNotificationSettingsClientAction mx-3 my-2">
            <DiscussNotificationSettings/>
        </div>
    `;
}

registry
    .category("actions")
    .add("mail.discuss_notification_settings_action", DiscussNotificationSettingsClientAction);
