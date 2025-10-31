import { CallPreview } from "@mail/discuss/call/common/call_preview";

import { Component, useState, useSubEnv } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class WelcomePage extends Component {
    static props = ["proceed?"];
    static template = "mail.WelcomePage";
    static components = { CallPreview };

    setup() {
        super.setup();
        this.isClosed = false;
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.rtc = useService("discuss.rtc");
        useSubEnv({ inWelcomePage: true });
        this.state = useState({
            userName: this.store.self.name || _t("Guest"),
            hasMicrophone: undefined,
            hasCamera: undefined,
        });
    }

    onKeydownInput(ev) {
        if (ev.key === "Enter") {
            this.joinChannel();
        }
    }

    async joinChannel() {
        if (!this.store.self_partner) {
            await this.store.self_guest?.updateGuestName(this.state.userName.trim());
        }
        browser.localStorage.setItem("discuss_call_preview_join_mute", !this.state.hasMicrophone);
        browser.localStorage.setItem(
            "discuss_call_preview_join_video",
            Boolean(this.state.hasCamera)
        );
        this.props.proceed?.();
    }

    getLoggedInAsText() {
        return _t("Logged in as %s", this.store.self.name);
    }

    get noActiveParticipants() {
        return !this.store.discuss.thread.rtc_session_ids.length;
    }

    /** @param {{ microphone?: boolean, camera?: boolean }} settings */
    onCallSettingsChanged(settings) {
        if (settings.microphone !== undefined) {
            this.state.hasMicrophone = settings.microphone;
        }
        if (settings.camera !== undefined) {
            this.state.hasCamera = settings.camera;
        }
    }
}
