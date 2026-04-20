import { Component, proxy, signal } from "@odoo/owl";

import { CallPreview } from "@mail/discuss/call/common/call_preview";
import { AvatarStack } from "@mail/discuss/core/common/avatar_stack";

import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { useLayoutEffect, useSubEnv } from "@web/owl2/utils";

export class WelcomePage extends Component {
    static props = ["proceed?"];
    static template = "mail.WelcomePage";
    static components = { AvatarStack, CallPreview };

    cameraPermissionOnMountChecked = false;

    setup() {
        super.setup();
        this.description = signal();
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.rtc = useService("discuss.rtc");
        useSubEnv({ inWelcomePage: true });
        this.state = proxy({
            userName: this.store.discuss.thread.getPersonaName(this.store.self) ?? "",
            activateCamera: 0,
            activateMicrophone: 0,
            hasMicrophone: undefined,
            hasCamera: undefined,
            isDescriptionLong: false,
            isDescriptionUnfolded: false,
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
        useLayoutEffect(
            (isDescriptionUnfolded, description) => {
                const descriptionEl = this.description();
                this.state.isDescriptionLong =
                    !isDescriptionUnfolded &&
                    description &&
                    descriptionEl?.scrollWidth > descriptionEl?.clientWidth;
            },
            () => [this.state.isDescriptionUnfolded, this.channel.description]
        );
    }

    onKeydownInput(ev) {
        if (ev.key === "Enter" && this.canJoin) {
            this.joinChannel();
        }
    }

    unfoldDescription() {
        if (this.state.isDescriptionUnfolded) {
            return;
        }
        this.state.isDescriptionUnfolded = true;
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

    get channel() {
        return this.store.discuss.thread.channel;
    }

    get showCallPreview() {
        return this.channel.default_display_mode === "video_full_screen";
    }

    get shouldShowMoreDescription() {
        return this.state.isDescriptionLong;
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
