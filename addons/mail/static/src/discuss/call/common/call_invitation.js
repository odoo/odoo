import { Action, ACTION_TAGS } from "@mail/core/common/action";
import { ActionList, CircleInlineAction } from "@mail/core/common/action_list";
import {
    acceptWithCamera,
    CallAction,
    joinAction,
    rejectAction,
} from "@mail/discuss/call/common/call_actions";
import { getCallActionComponent } from "@mail/discuss/call/common/call_action_list";
import { CallPreview } from "@mail/discuss/call/common/call_preview";
import { useAncestors } from "@mail/core/common/ancestor_plugin";

import { Component, computed, proxy, signal, types, useProps } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

/** Button to accept the call, spaced from the button next to it. */
class AcceptCallInlineAction extends CircleInlineAction {
    get marginClass() {
        return { ...super.marginClass, "o-me-0_5": true };
    }
}

export class CallInvitation extends Component {
    static template = "discuss.CallInvitation";
    static components = { ActionList, CallPreview };

    root = signal.ref();

    setup() {
        super.setup();
        this.rtc = useService("discuss.rtc");
        this.store = useService("mail.store");
        this.props = useProps({
            channel: types.instanceOf(this.store["discuss.channel"]),
        });
        this.ui = useService("ui");
        this.state = proxy({
            activateCamera: 0,
            activateMicrophone: 0,
            showCameraPreview: false,
            hasCamera: false,
            hasMicrophone: this.rtc.microphonePermission === "granted",
        });
        useAncestors({ inDiscussCallTheme: true });
    }

    /** @type {import("@mail/core/common/action_list").GetActionComponent} */
    getActionComponent(params) {
        if (params.inline && ["accept-with-camera", "join"].includes(params.action.id)) {
            return AcceptCallInlineAction;
        }
        return getCallActionComponent(params);
    }

    async joinCall() {
        const hasJoinedCall = await this.rtc.requestToggleCall(this.props.channel, {
            audio: this.state.hasMicrophone,
            camera: this.state.hasCamera,
        });
        if (!hasJoinedCall) {
            return;
        }
        this.props.channel.open({ focus: true });
        if (this.props.channel.default_display_mode === "video_full_screen") {
            await this.rtc.enterFullscreen();
        }
    }

    acceptOrRejectActions = computed(() => {
        const joinUpdated = {
            ...joinAction,
            onSelected: () => this.joinCall(),
        };
        const acceptWithCameraUpdated = {
            ...acceptWithCamera,
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
                channel: this.props.channel,
            }),
            new CallAction({
                id: "join",
                definition: joinUpdated,
                owner: this,
                store: this.store,
                channel: this.props.channel,
            }),
            new CallAction({
                id: "reject",
                definition: rejectAction,
                owner: this,
                store: this.store,
                channel: this.props.channel,
            }),
        ];
    });

    otherActions = computed(() => [
        new Action({
            id: "toggle-camera-preview",
            definition: {
                name: () =>
                    this.state.showCameraPreview
                        ? _t("Hide camera preview")
                        : _t("Show camera preview"),
                icon: () => (this.state.showCameraPreview ? "expand_less" : "expand_more"),
                onSelected: () => {
                    this.state.showCameraPreview = !this.state.showCameraPreview;
                    if (this.state.showCameraPreview) {
                        if (this.rtc.cameraPermission !== "denied") {
                            this.state.activateCamera++;
                        }
                        if (this.state.hasMicrophone) {
                            this.state.activateMicrophone++;
                        }
                        this.props.channel.self_member_id?.cancelInvitationTimeout();
                    } else {
                        this.props.channel.self_member_id?.startInvitationTimeout();
                    }
                },
                tags: () => [ACTION_TAGS.CALL_LAYOUT],
            },
            store: this.store,
        }),
    ]);

    get avatarTitle() {
        const channelName = this.props.channel.displayName;
        if (this.props.channel.channel_type === "chat") {
            return _t("View chat with %(channel_name)s", { channel_name: channelName });
        }
        return _t("View the %(channel_name)s channel", { channel_name: channelName });
    }

    get inviter() {
        return this.props.channel.self_member_id?.rtc_inviting_session_id?.channel_member_id;
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
