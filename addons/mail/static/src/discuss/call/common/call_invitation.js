import { Action, ACTION_TAGS } from "@mail/core/common/action";
import { ActionList } from "@mail/core/common/action_list";
import {
    acceptWithCamera,
    CallAction,
    joinAction,
    rejectAction,
} from "@mail/discuss/call/common/call_actions";
import { CallPreview } from "@mail/discuss/call/common/call_preview";

import { Component, useState, useSubEnv } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class CallInvitation extends Component {
    static props = ["thread"];
    static template = "discuss.CallInvitation";
    static components = { ActionList, CallPreview };

    setup() {
        super.setup();
        this.rtc = useService("discuss.rtc");
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.state = useState({
            activateCamera: 0,
            activateMicrophone: 0,
            showCameraPreview: false,
            hasCamera: false,
            hasMicrophone: this.rtc.microphonePermission === "granted",
        });
        useSubEnv({ inCallInvitation: true });
    }

    joinCall() {
        this.rtc.toggleCall(this.props.thread, {
            audio: this.state.hasMicrophone,
            camera: this.state.hasCamera,
        });
    }

    get acceptOrRejectActions() {
        const joinUpdated = {
            ...joinAction,
            btnClass: joinAction.btnClass + " o-me-0_5",
            onSelected: () => this.joinCall(),
        };
        const acceptWithCameraUpdated = {
            ...acceptWithCamera,
            btnClass: acceptWithCamera.btnClass + " o-me-0_5",
            onSelected: () => {
                this.state.hasCamera = true;
                this.joinCall();
            },
            condition: true,
        };
        return [
            new CallAction({
                id: "accept-with-camera",
                definition: acceptWithCameraUpdated,
                owner: this,
                store: this.store,
                thread: this.props.thread,
            }),
            new CallAction({
                id: "join",
                definition: joinUpdated,
                owner: this,
                store: this.store,
                thread: this.props.thread,
            }),
            new CallAction({
                id: "reject",
                definition: rejectAction,
                owner: this,
                store: this.store,
                thread: this.props.thread,
            }),
        ];
    }

    get otherActions() {
        return [
            new Action({
                id: "toggle-camera-preview",
                definition: {
                    name: () =>
                        this.state.showCameraPreview
                            ? _t("Hide camera preview")
                            : _t("Show camera preview"),
                    icon: () =>
                        this.state.showCameraPreview ? "fa fa-chevron-up" : "fa fa-chevron-down",
                    onSelected: () => {
                        this.state.showCameraPreview = !this.state.showCameraPreview;
                        if (this.rtc.cameraPermission !== "denied") {
                            this.state.activateCamera++;
                        }
                        if (this.state.hasMicrophone) {
                            this.state.activateMicrophone++;
                        }
                    },
                    tags: () => [ACTION_TAGS.CALL_LAYOUT],
                },
                store: this.store,
            }),
        ];
    }

    get avatarTitle() {
        const channelName = this.props.thread.displayName;
        if (this.props.thread.channel_type === "chat") {
            return _t("View chat with %(channel_name)s", { channel_name: channelName });
        }
        return _t("View the %(channel_name)s channel", { channel_name: channelName });
    }

    get inviter() {
        return this.props.thread.self_member_id?.rtc_inviting_session_id?.channel_member_id;
    }

    get incomingCallText() {
        if (this.props.thread.channel_type === "chat" || !this.inviter) {
            return _t("Incoming call");
        }
        return _t("Incoming call from %(inviter)s", { inviter: this.inviter.name });
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
