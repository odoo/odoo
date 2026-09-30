import { MESSAGE_SOUND } from "@mail/core/common/settings_model";
import { Component, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";

export class DiscussNotificationSettings extends Component {
    static props = {};
    static template = "mail.DiscussNotificationSettings";

    setup() {
        this.store = useService("mail.store");
        this.state = useState({
            selectedDuration: false,
        });
    }

    onChangeMessageSound() {
        if (this.store.settings.messageSound) {
            this.disableMessageSound();
        } else {
            this.enableMessageSound();
        }
    }

    enableMessageSound() {
        browser.localStorage.removeItem(MESSAGE_SOUND);
        this.store.settings._recomputeMessageSound++;
    }

    disableMessageSound() {
        browser.localStorage.setItem(MESSAGE_SOUND, false);
        this.store.settings._recomputeMessageSound++;
    }
}
