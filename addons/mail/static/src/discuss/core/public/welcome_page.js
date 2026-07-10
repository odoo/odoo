import { Component, proxy, types, useProps } from "@odoo/owl";

import { CallPreview } from "@mail/discuss/call/common/call_preview";
import { DiscussInvitationCard } from "@mail/core/public_web/discuss_invitation_card";

import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { useLayoutEffect, useSubEnv } from "@web/owl2/utils";
import { rpc } from "@web/core/network/rpc";

export class WelcomePage extends Component {
    static template = "mail.WelcomePage";
    static components = { CallPreview, DiscussInvitationCard };

    cameraPermissionOnMountChecked = false;

    setup() {
        super.setup();
        this.props = useProps({ proceed: types.function([]).optional() });
        this.store = useService("mail.store");
        this.rtc = useService("discuss.rtc");
        useSubEnv({ inWelcomePage: true });
        this.state = proxy({
            userName: this.store.discuss.thread.getPersonaName(this.store.self) ?? "",
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
        const joinOptions = this.store.self_user
            ? {}
            : {
                  guest_name: this.state.userName.trim(),
              };
        const storeData = await rpc(
            `/chat/${this.channel.id}/${this.channel.uuid}/join`,
            joinOptions
        );
        this.store.insert(storeData);
        browser.localStorage.setItem("discuss_call_preview_join_mute", !this.state.hasMicrophone);
        browser.localStorage.setItem(
            "discuss_call_preview_join_video",
            Boolean(this.state.hasCamera)
        );
        this.props.proceed?.();
    }

    get canJoin() {
        return Boolean(
            this.store.self_user || (this.state.userName.trim() && this.state.userName.length <= 60)
        );
    }

    get channel() {
        return this.store.discuss.thread.channel;
    }

    get showCallPreview() {
        return this.channel.default_display_mode === "video_full_screen";
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
