import { useLayoutEffect } from "@web/owl2/utils";
import { Action, ACTION_TAGS } from "@mail/core/common/action";
import { ActionList } from "@mail/core/common/action_list";
import {
    cameraOnAction,
    muteAction,
    quickActionSettings,
    quickVideoSettings,
} from "@mail/discuss/call/common/call_actions";
import { CallPermissionDialog } from "@mail/discuss/call/common/call_permission_dialog";
import { CallSettingsDialog } from "@mail/discuss/call/common/call_settings";
import { DeviceSelect } from "@mail/discuss/call/common/device_select";
import { SelfVideo } from "@mail/discuss/call/common/self_video";
import { closeStream } from "@mail/utils/common/misc";

import {
    Component,
    computed,
    onWillDestroy,
    proxy,
    signal,
    status,
    types,
    useOnChange,
    useProps,
} from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class CallPreview extends Component {
    static template = "mail.CallPreview";
    static components = { ActionList, DeviceSelect, SelfVideo };

    audioRef = signal.ref();

    setup() {
        this.props = useProps({
            activateCamera: types.number().optional(),
            activateMicrophone: types.number().optional(),
            hasSettingsAtBottom: types.boolean().optional(),
            onSettingsChanged: types
                .function([
                    types.object({
                        camera: types.boolean().optional(),
                        microphone: types.boolean().optional(),
                    }),
                ])
                .optional(),
        });
        this.dialog = useService("dialog");
        this.rtc = useService("discuss.rtc");
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.state = proxy({ audioStream: null, isCameraActive: false });
        useLayoutEffect(
            (audioEl, audioStream) => {
                if (audioEl && !audioEl.srcObject && audioStream) {
                    audioEl.srcObject = audioStream;
                }
            },
            () => [this.audioRef(), this.state.audioStream]
        );
        useOnChange(
            () => [this.state.isCameraActive],
            (isCameraActive) => this.props.onSettingsChanged?.({ camera: isCameraActive }),
            { initialRun: false }
        );
        if (this.hasRtcSupport) {
            useOnChange(
                () => [this.rtc.microphonePermission],
                (microphonePermission) => {
                    if (microphonePermission !== "granted") {
                        this.disableMicrophone();
                    }
                },
                { initialRun: false }
            );
            useOnChange(
                () => [this.store.settings.audioInputDeviceId],
                () => {
                    if (this.state.audioStream) {
                        closeStream(this.state.audioStream);
                        this.enableMicrophone();
                    }
                },
                { initialRun: false }
            );
            useOnChange(
                () => [this.store.settings.audioOutputDeviceId],
                (deviceId) => {
                    this.audioRef()
                        ?.setSinkId?.(deviceId)
                        .catch(() => {});
                },
                { initialRun: false }
            );
            onWillDestroy(() => {
                closeStream(this.state.audioStream);
            });
            useLayoutEffect(
                (activateCamera) => {
                    if (activateCamera > 0 && !this.state.isCameraActive) {
                        this.enableCamera();
                    }
                },
                () => [this.props.activateCamera]
            );
            useLayoutEffect(
                (activateMicrophone) => {
                    if (activateMicrophone > 0 && !this.state.audioStream) {
                        this.enableMicrophone();
                    }
                },
                () => [this.props.activateMicrophone]
            );
        }
    }

    get hasRtcSupport() {
        return Boolean(
            navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaStream
        );
    }

    get inWelcomePageMobile() {
        return this.env.inWelcomePage && this.ui.isSmall;
    }

    actions = computed(() => {
        const cameraOnActionUpdated = {
            ...cameraOnAction,
            isActive: () => this.state.isCameraActive,
            name: ({ action }) => (action.isActive ? _t("Turn camera off") : _t("Turn camera on")),
            onSelected: () => this.toggleCamera(),
            tags: (...args) => {
                const tags = cameraOnAction.tags?.(...args) ?? [];
                if (!args[0].action.isActive && this.rtc.cameraPermission !== "granted") {
                    tags.push(ACTION_TAGS.DANGER);
                }
                return tags;
            },
        };
        const muteActionUpdated = {
            ...muteAction,
            isActive: () => !this.state.audioStream,
            name: ({ action }) => (action.isActive ? _t("Unmute") : _t("Mute")),
            onSelected: () => this.toggleMic(),
        };
        const videoBlurAction = {
            condition: () => this.state.isCameraActive,
            icon: () => "image",
            iconClass: () => "oi oi-fw",
            isActive: ({ store }) => store.settings.useBlur,
            name: ({ action }) =>
                action.isActive ? _t("Disable background blur") : _t("Enable background blur"),
            onSelected: ({ store }) => {
                store.settings.useBlur = !store.settings.useBlur;
            },
            tags: ({ action }) => (action.isActive ? [ACTION_TAGS.SUCCESS] : []),
        };
        const callAudioActions = [
            new Action({
                id: "toggle-microphone",
                owner: this,
                definition: muteActionUpdated,
                store: this.store,
            }),
        ];
        const callVideoActions = [
            new Action({
                id: "toggle-camera",
                owner: this,
                definition: cameraOnActionUpdated,
                store: this.store,
            }),
        ];
        if (this.props.hasSettingsAtBottom) {
            callVideoActions.push(
                new Action({
                    id: "video-blur",
                    owner: this,
                    definition: videoBlurAction,
                    store: this.store,
                })
            );
        } else {
            callAudioActions.push(
                new Action({
                    id: "audio-settings",
                    owner: this,
                    definition: quickActionSettings,
                    store: this.store,
                })
            );
            callVideoActions.push(
                new Action({
                    id: "video-settings",
                    owner: this,
                    definition: quickVideoSettings,
                    store: this.store,
                })
            );
        }

        return [callAudioActions, callVideoActions];
    });

    async enableMicrophone() {
        if (
            this.rtc.microphonePermission !== "granted" &&
            !(await this.rtc.askForBrowserPermission({ audio: true }))
        ) {
            return;
        }
        this.state.audioStream = await navigator.mediaDevices.getUserMedia({
            audio: this.store.settings.audioConstraints,
        });
        if (status(this) === "destroyed") {
            closeStream(this.state.audioStream);
            return;
        }
        if (this.audioRef()) {
            this.audioRef().srcObject = this.state.audioStream;
        }
        this.props.onSettingsChanged?.({ microphone: true });
    }

    disableMicrophone() {
        closeStream(this.state.audioStream);
        this.state.audioStream = null;
        if (this.audioRef()) {
            this.audioRef().srcObject = null;
        }
        this.props.onSettingsChanged?.({ microphone: false });
    }

    async toggleMic() {
        if (this.state.audioStream) {
            this.disableMicrophone();
            return;
        }
        if (this.rtc.microphonePermission === "prompt") {
            this.dialog.add(CallPermissionDialog, {
                media: "microphone",
                useMicrophone: () => this.enableMicrophone(),
                useCamera: () => this.enableCamera(),
            });
            return;
        }
        await this.enableMicrophone();
    }

    enableCamera() {
        this.state.isCameraActive = true;
    }

    disableCamera() {
        this.state.isCameraActive = false;
    }

    async toggleCamera() {
        if (this.state.isCameraActive) {
            this.disableCamera();
            return;
        }
        if (this.rtc.cameraPermission === "prompt") {
            this.dialog.add(CallPermissionDialog, {
                media: "camera",
                useMicrophone: () => this.enableMicrophone(),
                useCamera: () => this.enableCamera(),
            });
            return;
        }
        this.enableCamera();
    }

    onClickSettings() {
        this.dialog.add(CallSettingsDialog, {});
    }

    onCameraStateChange(isCameraActive) {
        if (this.state.isCameraActive !== isCameraActive) {
            this.state.isCameraActive = isCameraActive;
        }
    }
}
