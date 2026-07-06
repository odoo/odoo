import { Component, signal } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useNavigation } from "@web/core/navigation/navigation";

export class DiscussNotificationSettings extends Component {
    static template = "mail.DiscussNotificationSettings";

    notificationsRef = signal.ref();

    setup() {
        this.store = useService("mail.store");
        this.focusedLabel = signal(this.store.self_user.res_users_settings_id.channelNotifications);
        useNavigation(this.notificationsRef, {
            shouldFocusChildInput: false,
            hotkeys: {
                enter: {
                    allowRepeat: false,
                },
                space: {
                    callback: (navigator) => navigator.activeItem?.select(),
                    allowRepeat: false,
                },
            },
            isNavigationAvailable: ({ target }) =>
                this.notificationsRef()?.contains(target) && target === document.activeElement,
        });
    }

    onChangeMessageSound() {
        this.store.settings.messageSound = !this.store.settings.messageSound;
    }

    /**
     * Prevent the native button click from repeating while Enter is held down.
     *
     * @param {KeyboardEvent} ev
     */
    onKeydownOption(ev) {
        if (ev.key === "Enter" && ev.repeat) {
            ev.preventDefault();
        }
    }
}
