import { useLayoutEffect, useState, useSubEnv } from "@web/owl2/utils";
import { CallPreview } from "@mail/discuss/call/common/call_preview";

import { Component, markup } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class WelcomePage extends Component {
    static props = ["proceed?"];
    static template = "mail.WelcomePage";
    static components = { CallPreview };

    cameraPermissionOnMountChecked = false;

    setup() {
        super.setup();
        this.isClosed = false;
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.rtc = useService("discuss.rtc");
        useSubEnv({ inWelcomePage: true });
        this.state = useState({
            userName: this.store.self_user?.name || "",
            activateCamera: 0,
            activateMicrophone: 0,
            hasMicrophone: undefined,
            hasCamera: undefined,
        });
        useLayoutEffect(
            (showCallPreview, cameraPermission, microphonePermission) => {
                if (!showCallPreview) {
                    return;
                }
                if (cameraPermission === "prompt" && !this.cameraPermissionOnMountChecked) {
                    this.rtc.showMediaPermissionDialog("camera");
                }
                if (cameraPermission === "granted") {
                    this.state.activateCamera++;
                }
                if (microphonePermission === "granted") {
                    this.state.activateMicrophone++;
                }
                this.cameraPermissionOnMountChecked = Boolean(cameraPermission);
            },
            () => [this.showCallPreview, this.rtc.cameraPermission, this.rtc.microphonePermission]
        );
    }

    onKeydownInput(ev) {
        if (ev.key === "Enter" && this.canJoin) {
            this.joinChannel();
        }
    }

    async joinChannel() {
        if (!this.store.self_user) {
            await this.store.self_guest?.updateGuestName(this.state.userName.trim());
        }
        browser.localStorage.setItem("discuss_call_preview_join_mute", !this.state.hasMicrophone);
        browser.localStorage.setItem(
            "discuss_call_preview_join_video",
            Boolean(this.state.hasCamera)
        );
        this.props.proceed?.();
    }

    get canJoin() {
        return (
            this.store.self_user || (this.state.userName.trim() && this.state.userName.length <= 60)
        );
    }

    get noActiveParticipants() {
        return !this.store.discuss.thread.channel.hasRtcSessionActive;
    }

    get subtitle() {
        return _t(
            "%(open_tag_1)swith%(close_tag_1)s %(open_tag_2)s%(company_name)s%(close_tag_2)s",
            {
                open_tag_1: markup`<span class="text-muted">`,
                close_tag_1: markup`</span>`,
                open_tag_2: markup`<span>`,
                close_tag_2: markup`</span>`,
                company_name: this.store.companyName,
            }
        );
    }

    get showCallPreview() {
        return this.store.discuss.thread.channel.default_display_mode === "video_full_screen";
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
