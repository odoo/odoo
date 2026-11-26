import { Action, ACTION_TAGS, PANEL_CONTAINER_TYPE } from "@mail/core/common/action";
import { ActionList } from "@mail/core/common/action_list";
import {
    cameraOnAction,
    muteAction,
    quickActionSettings,
    quickVideoSettings,
} from "@mail/discuss/call/common/call_actions";
import { CallPermissionDialog } from "@mail/discuss/call/common/call_permission_dialog";
import { CallSettingsDialog } from "@mail/discuss/call/common/call_settings";
import { CameraPreview } from "@mail/discuss/call/common/camera_preview";
import { DeviceSelect } from "@mail/discuss/call/common/device_select";
import { closeStream, hasRtcSupport } from "@mail/utils/common/misc";
import { useAncestors } from "@mail/core/common/ancestor_plugin";

import {
    Component,
    computed,
    onWillDestroy,
    onWillUnmount,
    proxy,
    signal,
    types,
    useOnChange,
    usePlugin,
    useProps,
    useScope,
} from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { UIPlugin } from "@web/core/ui/ui_plugin";
import { useService } from "@web/core/utils/hooks";

export class CallPreview extends Component {
    static template = "mail.CallPreview";
<<<<<<< 18f033cd7fa36eac97435f6ec8ed2572d767649c
    static components = { ActionList, CameraPreview, DeviceSelect };
||||||| c7f4cc9f344027a969d8604a8ec900fd031472e8
    static components = { ActionList, DeviceSelect };
=======
    static components = { ActionList, DeviceSelect };
    /** ids of the latest camera and microphone requests, older ones are discarded */
    requestIds = { camera: 0, mic: 0 };
>>>>>>> 947d4143bdd3b5ee7523b2e8e4cf43854a5afa3b

    audioRef = signal.ref();
    /**
     * The preview has no panel of its own: the quick settings open theirs in a dropdown above it.
     *
     * @type {import("@mail/core/common/action_list").ActionPanelContainer}
     */
    panelContainer = {
        type: PANEL_CONTAINER_TYPE.DROPDOWN,
        position: "top-end",
        menuClass: "p-1 overflow-x-hidden",
    };

    scope = useScope();

    setup() {
        this.ancestors = useAncestors();
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
        this.ui = usePlugin(UIPlugin);
        this.state = proxy({ audioStream: null, isCameraActive: false });
        useOnChange(
            () => [this.audioRef(), this.state.audioStream],
            (audioEl, audioStream) => {
                if (audioEl && !audioEl.srcObject && audioStream) {
                    audioEl.srcObject = audioStream;
                }
            }
        );
        useOnChange(
            () => [this.state.isCameraActive],
            (isCameraActive) => this.props.onSettingsChanged?.({ camera: isCameraActive }),
            { initialRun: false }
        );
        if (hasRtcSupport()) {
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
            onWillUnmount(() => {
                // A media element with an active srcObject is kept alive by the
                // browser once detached, retaining this component through it.
                const audioEl = this.audioRef();
                if (audioEl) {
                    audioEl.srcObject = null;
                    audioEl.load();
                }
            });
            onWillDestroy(() => {
                closeStream(this.state.audioStream);
            });
            useOnChange(
                () => [this.props.activateCamera],
                (activateCamera) => {
                    if (activateCamera > 0 && !this.state.isCameraActive) {
                        this.enableCamera();
                    }
                }
            );
            useOnChange(
                () => [this.props.activateMicrophone],
                (activateMicrophone) => {
                    if (activateMicrophone > 0 && !this.state.audioStream) {
                        this.enableMicrophone();
                    }
                }
            );
        }
    }

    get inWelcomePageMobile() {
        return this.ancestors.inWelcomePage && this.ui.isSmall();
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
                ancestors: this.ancestors,
                owner: this,
                definition: muteActionUpdated,
                store: this.store,
            }),
        ];
        const callVideoActions = [
            new Action({
                id: "toggle-camera",
                ancestors: this.ancestors,
                owner: this,
                definition: cameraOnActionUpdated,
                store: this.store,
            }),
        ];
        if (this.props.hasSettingsAtBottom) {
            callVideoActions.push(
                new Action({
                    id: "video-blur",
                    ancestors: this.ancestors,
                    owner: this,
                    definition: videoBlurAction,
                    store: this.store,
                })
            );
        } else {
            callAudioActions.push(
                new Action({
                    id: "audio-settings",
                    ancestors: this.ancestors,
                    owner: this,
                    definition: quickActionSettings,
                    store: this.store,
                })
            );
            callVideoActions.push(
                new Action({
                    id: "video-settings",
                    ancestors: this.ancestors,
                    owner: this,
                    definition: quickVideoSettings,
                    store: this.store,
                })
            );
        }

        return [callAudioActions, callVideoActions];
    });

    async enableMicrophone() {
        const micRequestId = ++this.requestIds.mic;
        if (
            this.rtc.microphonePermission !== "granted" &&
            !(await this.rtc.askForBrowserPermission({ audio: true }))
        ) {
            return;
        }
        const audioStream = await navigator.mediaDevices.getUserMedia({
            audio: this.store.settings.audioConstraints,
        });
<<<<<<< 18f033cd7fa36eac97435f6ec8ed2572d767649c
        if (this.scope.isDestroyed()) {
            closeStream(this.state.audioStream);
||||||| c7f4cc9f344027a969d8604a8ec900fd031472e8
        if (status(this) === "destroyed") {
            closeStream(this.state.audioStream);
=======
        if (status(this) === "destroyed" || micRequestId !== this.requestIds.mic) {
            closeStream(audioStream);
>>>>>>> 947d4143bdd3b5ee7523b2e8e4cf43854a5afa3b
            return;
        }
        this.state.audioStream = audioStream;
        if (this.audioRef()) {
            this.audioRef().srcObject = this.state.audioStream;
        }
        this.props.onSettingsChanged?.({ microphone: true });
    }

    disableMicrophone() {
        this.requestIds.mic++;
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

<<<<<<< 18f033cd7fa36eac97435f6ec8ed2572d767649c
    enableCamera() {
        this.state.isCameraActive = true;
||||||| c7f4cc9f344027a969d8604a8ec900fd031472e8
    async enableCamera() {
        if (
            this.rtc.cameraPermission !== "granted" &&
            !(await this.rtc.askForBrowserPermission({ video: true }))
        ) {
            return;
        }
        this.state.videoStream = await navigator.mediaDevices.getUserMedia({
            video: this.store.settings.cameraConstraints,
        });
        if (status(this) === "destroyed") {
            closeStream(this.state.videoStream);
            return;
        }
        if (this.videoRef()) {
            this.videoRef().srcObject = this.state.videoStream;
        }
        this.props.onSettingsChanged?.({ camera: true });
        if (this.store.settings.useBlur) {
            await this.enableBlur();
        }
=======
    async enableCamera() {
        const cameraRequestId = ++this.requestIds.camera;
        if (
            this.rtc.cameraPermission !== "granted" &&
            !(await this.rtc.askForBrowserPermission({ video: true }))
        ) {
            return;
        }
        const videoStream = await navigator.mediaDevices.getUserMedia({
            video: this.store.settings.cameraConstraints,
        });
        if (status(this) === "destroyed" || cameraRequestId !== this.requestIds.camera) {
            closeStream(videoStream);
            return;
        }
        this.state.videoStream = videoStream;
        if (this.videoRef()) {
            this.videoRef().srcObject = this.state.videoStream;
        }
        this.props.onSettingsChanged?.({ camera: true });
        if (this.store.settings.useBlur) {
            await this.enableBlur();
        }
>>>>>>> 947d4143bdd3b5ee7523b2e8e4cf43854a5afa3b
    }

    disableCamera() {
<<<<<<< 18f033cd7fa36eac97435f6ec8ed2572d767649c
        this.state.isCameraActive = false;
||||||| c7f4cc9f344027a969d8604a8ec900fd031472e8
        closeStream(this.state.videoStream);
        this.state.videoStream = null;
        this.state.blurManager?.close();
        this.state.blurManager = undefined;
        if (this.videoRef()) {
            this.videoRef().srcObject = null;
        }
        this.props.onSettingsChanged?.({ camera: false });
=======
        this.requestIds.camera++;
        closeStream(this.state.videoStream);
        this.state.videoStream = null;
        this.state.blurManager?.close();
        this.state.blurManager = undefined;
        if (this.videoRef()) {
            this.videoRef().srcObject = null;
        }
        this.props.onSettingsChanged?.({ camera: false });
>>>>>>> 947d4143bdd3b5ee7523b2e8e4cf43854a5afa3b
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
<<<<<<< 18f033cd7fa36eac97435f6ec8ed2572d767649c
        this.enableCamera();
||||||| c7f4cc9f344027a969d8604a8ec900fd031472e8
        await this.enableCamera();
    }

    async enableBlur() {
        this.store.settings.useBlur = true;
        if (!this.videoRef()) {
            return;
        }
        try {
            this.state.blurManager = await this.rtc.applyBlurEffect(this.state.videoStream);
            this.videoRef().srcObject = await this.state.blurManager.stream;
        } catch (_e) {
            this.notification.add(_e.message, { type: "warning" });
            this.disableBlur();
        }
    }

    disableBlur() {
        this.store.settings.useBlur = false;
        if (this.videoRef()) {
            this.videoRef().srcObject = this.state.videoStream;
        }
        this.state.blurManager?.close();
        this.state.blurManager = undefined;
    }

    toggleBlur() {
        if (this.state.blurManager) {
            this.disableBlur();
            return;
        }
        this.enableBlur();
=======
        await this.enableCamera();
    }

    async enableBlur() {
        this.store.settings.useBlur = true;
        if (!this.videoRef()) {
            return;
        }
        const cameraRequestId = this.requestIds.camera;
        this.state.blurManager?.close();
        try {
            this.state.blurManager = await this.rtc.applyBlurEffect(this.state.videoStream);
            this.videoRef().srcObject = await this.state.blurManager.stream;
        } catch (_e) {
            if (cameraRequestId !== this.requestIds.camera) {
                return;
            }
            this.notification.add(_e.message, { type: "warning" });
            this.disableBlur();
        }
    }

    disableBlur() {
        this.store.settings.useBlur = false;
        if (this.videoRef()) {
            this.videoRef().srcObject = this.state.videoStream;
        }
        this.state.blurManager?.close();
        this.state.blurManager = undefined;
    }

    toggleBlur() {
        if (this.state.blurManager) {
            this.disableBlur();
            return;
        }
        this.enableBlur();
>>>>>>> 947d4143bdd3b5ee7523b2e8e4cf43854a5afa3b
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
