import { Component, xml } from "@odoo/owl";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { useService } from "@web/core/utils/hooks";
import { DiscussNotificationSettingsClientAction } from "./discuss_notification_settings_client_action";
import { NotificationMuteSettings } from "./notification_mute_settings";
import { Dialog } from "@web/core/dialog/dialog";

class NotificationDialog extends Component {
    static props = ["close?"];
    static components = { Dialog, DiscussNotificationSettingsClientAction };
    static template = xml`
        <Dialog size="'md'" footer="false">
            <DiscussNotificationSettingsClientAction/>
        </Dialog>
    `;
}

export class NotificationSettings extends Component {
    static components = { ActionPanel, NotificationMuteSettings };
    static props = ["hasSizeConstraints?", "thread", "close?", "className?"];
    static template = "discuss.NotificationSettings";

    setup() {
        this.store = useService("mail.store");
        this.dialog = useService("dialog");
    }

    onClickAllConversationsMuted() {
        this.dialog.add(NotificationDialog);
    }
}
