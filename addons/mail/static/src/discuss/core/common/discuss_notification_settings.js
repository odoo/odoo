import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class DiscussNotificationSettings extends Component {
    static template = "mail.DiscussNotificationSettings";

    setup() {
        this.store = useService("mail.store");
    }

    onChangeMessageSound() {
        this.store.settings.messageSound = !this.store.settings.messageSound;
    }

    selectNotification(label) {
        if (label === this.store.settings.channel_notifications) {
            return;
        }
        this.store.settings.setCustomNotifications(label);
    }

    getTabIndex(notif) {
        return notif.label === this.store.settings.channel_notifications ? 0 : -1;
    }

    onKeydownNotification(ev, label) {
        switch (ev.key) {
            case "ArrowDown":
                this.moveFocus(ev.currentTarget, 1);
                break;

            case "ArrowUp":
                this.moveFocus(ev.currentTarget, -1);
                break;
        }
    }

    moveFocus(currentEl, direction) {
        const group = currentEl.closest(".o-mail-DiscussNotificationSettings-options");
        const items = [...group.querySelectorAll(".o-mail-DiscussNotificationSettings-option")];
        const currentIndex = items.indexOf(currentEl);
        const nextIndex = (currentIndex + direction + items.length) % items.length;

        items[currentIndex].tabIndex = -1;
        items[nextIndex].tabIndex = 0;
        items[nextIndex].focus();
    }
}
