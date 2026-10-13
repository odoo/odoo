import { Component, proxy, signal, types, useProps } from "@odoo/owl";

import { CallPreview } from "@mail/discuss/call/common/call_preview";
import { AvatarStack } from "@mail/discuss/core/common/avatar_stack";
import { useAncestors } from "@mail/core/common/ancestor_plugin";

import { useService } from "@web/core/utils/hooks";
import { useLayoutEffect } from "@web/owl2/utils";

export class WelcomePage extends Component {
    static template = "mail.WelcomePage";
    static components = { AvatarStack, CallPreview };

    isMediaPermissionsChecked = false;

    setup() {
        super.setup();
        this.props = useProps({ proceed: types.function([]).optional() });
        this.description = signal();
        this.busService = useService("bus_service");
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.rtc = useService("discuss.rtc");
        useAncestors({ inDiscussCallTheme: true, inWelcomePage: true });
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
                if (!this.isMediaPermissionsChecked) {
                    this.isMediaPermissionsChecked = true;
                    this.rtc.showMeetingMediaPermissionDialog();
                }
                if (cameraPermission === "granted") {
                    this.state.activateCamera++;
                }
                if (microphonePermission === "granted") {
                    this.state.activateMicrophone++;
                }
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
        const guestName = this.state.userName.trim();
        if (!this.store.self_user && this.store.self_guest?.id > 0) {
            await this.store.self_guest.updateGuestName(guestName);
        }
        await this.store.fetchStoreData("/discuss/channel/join_from_invitation", {
            channel_id: this.channel.id,
            email_token: this.store.invitation_email_token,
            guest_name: guestName,
            invitation_token: this.channel.uuid,
        });
        if (this.store.guest_token) {
            this.busService.addChannel(`mail.guest_${this.store.guest_token}`);
        }
        window.localStorage.setItem("discuss_call_preview_join_mute", !this.state.hasMicrophone);
        window.localStorage.setItem(
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
