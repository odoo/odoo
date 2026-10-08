import { Component, signal } from "@odoo/owl";
import { useNavigation } from "@web/core/navigation/navigation";
import { useService } from "@web/core/utils/hooks";

export class DiscussNotificationSettings extends Component {
    static template = "mail.DiscussNotificationSettings";

    notificationsRef = signal.ref();

    setup() {
        this.store = useService("mail.store");
        this.focusedNotification = signal(
            this.store.self_user.res_users_settings_id.channelNotifications
        );
        useNavigation(this.notificationsRef, {
            shouldFocusChildInput: false,
            hotkeys: {
                space: (navigator) => navigator.activeItem?.select(),
            },
            // Hovering another option must not change the keyboard activation target.
            isNavigationAvailable: ({ target }) =>
                this.notificationsRef()?.contains(target) && target === document.activeElement,
        });
    }

    onChangeMessageSound() {
        this.store.settings.messageSound = !this.store.settings.messageSound;
    }
}
