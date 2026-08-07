import { closeStream } from "@mail/utils/common/misc";

import {
    Component,
    onMounted,
    onWillDestroy,
    proxy,
    signal,
    status,
    types,
    useOnChange,
    useProps,
} from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class SelfVideo extends Component {
    static template = "discuss.SelfVideo";

    videoRef = signal.ref();

    setup() {
        this.notification = useService("notification");
        this.props = useProps({
            onCameraStateChange: types.function([types.boolean()]).optional(() => () => {}),
        });
        this.rtc = useService("discuss.rtc");
        this.store = useService("mail.store");
        this.state = proxy({ blurManager: null, blurStream: null, videoStream: null });
        onMounted(() => this.enableCamera());
        useOnChange(
            () => [this.videoRef(), this.state.videoStream, this.state.blurStream],
            (videoEl, videoStream, blurStream) => {
                if (!videoEl) {
                    return;
                }
                videoEl.srcObject = blurStream ?? videoStream ?? null;
            }
        );
        if (this.hasRtcSupport) {
            useOnChange(
                () => [this.rtc.cameraPermission],
                (cameraPermission) => {
                    if (cameraPermission !== "granted") {
                        this.disableCamera();
                    } else if (!this.state.videoStream) {
                        this.enableCamera();
                    }
                },
                { initialRun: false }
            );
            useOnChange(
                () => [this.store.settings.cameraInputDeviceId],
                () => {
                    if (this.state.videoStream) {
                        closeStream(this.state.videoStream);
                        this.enableCamera();
                    }
                },
                { initialRun: false }
            );
            useOnChange(
                () => [this.store.settings.useBlur],
                (useBlur) => {
                    if (useBlur) {
                        this.enableBlur();
                    } else {
                        this.disableBlur();
                    }
                },
                { initialRun: false }
            );
            useOnChange(
                () => [
                    this.store.settings.edgeBlurAmount,
                    this.store.settings.backgroundBlurAmount,
                ],
                (edgeBlurAmount, backgroundBlurAmount) => {
                    if (this.state.blurManager) {
                        this.state.blurManager.edgeBlur = edgeBlurAmount;
                        this.state.blurManager.backgroundBlur = backgroundBlurAmount;
                    }
                },
                { initialRun: false }
            );
            onWillDestroy(() => {
                closeStream(this.state.videoStream);
                this.state.blurManager?.close();
            });
        }
    }

    get hasRtcSupport() {
        return Boolean(
            navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaStream
        );
    }

    async enableCamera() {
        if (
            this.rtc.cameraPermission !== "granted" &&
            !(await this.rtc.askForBrowserPermission({ video: true }))
        ) {
            this.props.onCameraStateChange(false);
            return;
        }
        this.state.videoStream = await navigator.mediaDevices.getUserMedia({
            video: this.store.settings.cameraConstraints,
        });
        if (status(this) === "destroyed") {
            closeStream(this.state.videoStream);
            return;
        }
        this.props.onCameraStateChange(true);
        if (this.store.settings.useBlur) {
            await this.enableBlur();
        }
    }

    disableCamera() {
        closeStream(this.state.videoStream);
        this.state.videoStream = null;
        this.closeBlurManager();
        this.props.onCameraStateChange(false);
    }

    async enableBlur() {
        if (!this.state.videoStream) {
            return;
        }
        this.closeBlurManager();
        this.store.settings.useBlur = true;
        try {
            this.state.blurManager = await this.rtc.applyBlurEffect(this.state.videoStream);
            this.state.blurStream = await this.state.blurManager.stream;
        } catch (_e) {
            this.notification.add(_e.message, { type: "warning" });
            this.disableBlur();
        }
    }

    disableBlur() {
        this.store.settings.useBlur = false;
        this.closeBlurManager();
    }

    closeBlurManager() {
        this.state.blurManager?.close();
        this.state.blurManager = null;
        this.state.blurStream = null;
    }
}
