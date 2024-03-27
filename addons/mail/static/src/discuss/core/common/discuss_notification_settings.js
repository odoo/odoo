import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class DiscussNotificationSettings extends Component {
    static props = ["*"];
    static template = "mail.DiscussNotificationSettings";

    setup() {
        this.store = useState(useService("mail.store"));
        this.state = useState({
            selectedMute: false,
        });
    }

    get displayMuteMenu() {
        return this.state.openMuteMenu || this.store.settings.mute_until_dt;
    }

    onChangeDisplayMute(ev) {
        this.state.openMuteMenu = ev.target.checked;
        if (!this.state.openMuteMenu) {
            this.store.settings.setMuteDuration(false);
            return;
        }
        // If the user opens the mute menu, we set the default mute duration to forever
        this.store.settings.selected_mute_duration = this.store.settings.MUTES.find(
            (m) => m.id === "forever"
        ).value;
        this.store.settings.setMuteDuration(-1);
    }

    onChangeMuteDuration(ev) {
        this.store.settings.selected_mute_duration = ev.target.value;
        this.store.settings.setMuteDuration(parseInt(ev.target.value));
    }

    onChangeUseDesktopNotif(ev) {
        this.store.settings.setUseDesktopNotif(ev.target.checked);
    }

    onChangeCustomNotifications(value) {
        this.store.settings.setCustomNotifications(value);
    }
}
