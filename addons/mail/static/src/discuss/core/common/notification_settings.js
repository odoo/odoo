import { Component, signal, xml } from "@odoo/owl";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { DiscussNotificationSettingsClientAction } from "./discuss_notification_settings_client_action";
import { Dialog } from "@web/core/dialog/dialog";
import { DROPDOWN_NESTING } from "@web/core/dropdown/_behaviours/dropdown_nesting";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useHover } from "@mail/utils/common/hooks";

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
    static components = { ActionPanel, Dropdown, DropdownItem };
    static props = ["channel", "className?", "close?"];
    static template = "discuss.NotificationSettings";

    setup() {
        this.store = useService("mail.store");
        this.dialog = useService("dialog");
        this.ui = useService("ui");
        this.DROPDOWN_NESTING = DROPDOWN_NESTING;
        this.muteConversationDropdownState = useDropdownState();
        this.muteButton = signal();
        this.muteMenu = signal();
        this.muteConversationHover = useHover([this.muteButton, this.muteMenu], {
            onHover: () => (this.muteConversationDropdownState.isOpen = true),
            onAway: () => (this.muteConversationDropdownState.isOpen = false),
        });
    }

    setMute(minutes) {
        this.store.settings.setMuteDuration(minutes, this.props.channel);
        this.props.close?.();
    }

    onClickAllConversationsMuted() {
        this.dialog.add(NotificationDialog);
    }
}
