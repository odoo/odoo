import {
    Component,
    onMounted,
    onPatched,
    proxy,
    signal,
    types,
    useOnChange,
    usePlugin,
    useProps,
} from "@odoo/owl";

import { CallPreview } from "@mail/discuss/call/common/call_preview";
import { AvatarStack } from "@mail/discuss/core/common/avatar_stack";
import { useAncestors } from "@mail/core/common/ancestor_plugin";

import { UIPlugin } from "@web/core/ui/ui_plugin";
import { useService } from "@web/core/utils/hooks";
import { redirect } from "@web/core/utils/urls";

export class WelcomePage extends Component {
    static template = "mail.WelcomePage";
    static components = { AvatarStack, CallPreview };

    isMediaPermissionsChecked = false;

    setup() {
        super.setup();
        this.props = useProps({ proceed: types.function([]).optional() });
        this.description = signal();
        this.busService = useService("bus_service");
        this.imStatusService = useService("im_status");
        this.store = useService("mail.store");
        this.ui = usePlugin(UIPlugin);
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
            isJoining: false,
        });
        useOnChange(
            () => [this.showCallPreview, this.rtc.cameraPermission, this.rtc.microphonePermission],
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
            }
        );
        onMounted(() => this.updateIsDescriptionLong());
        onPatched(() => this.updateIsDescriptionLong());
    }

    /** Measures the rendered description, hence after mount/patch. */
    updateIsDescriptionLong() {
        const descriptionEl = this.description();
        this.state.isDescriptionLong =
            !this.state.isDescriptionUnfolded &&
            this.channel.description &&
            descriptionEl?.scrollWidth > descriptionEl?.clientWidth;
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
        if (this.state.isJoining) {
            return;
        }
        this.state.isJoining = true;
        const guestName = this.state.userName.trim();
        const isNewGuest = !this.store.self_user && !(this.store.self_guest?.id > 0);
        try {
            if (!this.store.self_user && this.store.self_guest?.id > 0) {
                await this.store.self_guest.updateGuestName(guestName);
            }
            await this.store.fetchStoreData("/discuss/channel/join_from_invitation", {
                channel_id: this.channel.id,
                email_token: this.store.invitation_email_token,
                guest_name: guestName,
                invitation_token: this.channel.uuid,
            });
        } finally {
            this.state.isJoining = false;
        }
        if (isNewGuest) {
            this.busService.restart();
            this.imStatusService.updateBusPresence();
        }
        window.localStorage.setItem("discuss_call_preview_join_mute", !this.state.hasMicrophone);
        window.localStorage.setItem(
            "discuss_call_preview_join_video",
            Boolean(this.state.hasCamera)
        );
        if (this.store.self_user?.share === false) {
            redirect(`/odoo/action-mail.action_discuss?active_id=${this.channel.id}`);
            return;
        }
        this.props.proceed?.();
    }

    get canJoin() {
        return (
            !this.state.isJoining &&
            (this.store.self_user ||
                (this.state.userName.trim() && this.state.userName.length <= 60))
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
