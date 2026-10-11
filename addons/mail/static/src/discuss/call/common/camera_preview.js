import { closeStream, hasRtcSupport } from "@mail/utils/common/misc";

import {
    Component,
    onMounted,
    onWillDestroy,
    proxy,
    signal,
    types,
    useOnChange,
    useProps,
    useScope,
} from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class CameraPreview extends Component {
    static template = "discuss.CameraPreview";

    blurRequestId = 0;
    isEnablingCamera = false;
    isRestartQueued = false;
    scope = useScope();
    videoRef = signal.ref();

    setup() {
        this.notification = useService("notification");
        this.props = useProps({
            onCameraStateChange: types.function([types.boolean()]).optional(() => () => {}),
        });
        this.rtc = useService("discuss.rtc");
        this.state = proxy({ blurManager: null, blurStream: null, videoStream: null });
        this.store = useService("mail.store");
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
        if (hasRtcSupport()) {
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
                    if (!this.state.videoStream) {
                        return;
                    }
                    if (this.isEnablingCamera) {
                        this.isRestartQueued = true;
                    } else {
                        this.restartCamera();
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

    cancelBlur() {
        this.blurRequestId++;
        this.state.blurManager?.close();
        this.state.blurManager = null;
        this.state.blurStream = null;
    }

    disableBlur() {
        this.store.settings.useBlur = false;
        this.cancelBlur();
    }

    disableCamera() {
        this.isRestartQueued = false;
        this.stopCamera();
        this.props.onCameraStateChange(false);
    }

    async enableBlur() {
        const videoStream = this.state.videoStream;
        if (!videoStream) {
            return;
        }
        const requestId = ++this.blurRequestId;
        const isStale = () => this.scope.isDestroyed() || requestId !== this.blurRequestId;
        let blurManager;
        try {
            blurManager = this.rtc.applyBlurEffect(videoStream);
            const blurStream = await blurManager.stream;
            if (isStale()) {
                blurManager.close();
                return;
            }
            this.state.blurManager?.close();
            this.state.blurManager = blurManager;
            this.state.blurStream = blurStream;
        } catch (e) {
            blurManager?.close();
            if (isStale()) {
                return;
            }
            this.notification.add(e.message, { type: "warning" });
            if (!this.state.blurManager) {
                this.disableBlur();
            }
        }
    }

    async enableCamera() {
        if (this.isEnablingCamera) {
            return;
        }
        this.isEnablingCamera = true;
        try {
            if (
                this.rtc.cameraPermission !== "granted" &&
                !(await this.rtc.askForBrowserPermission({ video: true }))
            ) {
                this.props.onCameraStateChange(false);
                return;
            }
            const stream = await navigator.mediaDevices.getUserMedia({
                video: this.store.settings.cameraConstraints,
            });
            if (this.scope.isDestroyed()) {
                closeStream(stream);
                return;
            }
            this.state.videoStream = stream;
            this.props.onCameraStateChange(true);
            if (this.store.settings.useBlur) {
                await this.enableBlur();
            }
        } catch {
            this.disableCamera();
        } finally {
            this.isEnablingCamera = false;
            if (this.isRestartQueued) {
                this.isRestartQueued = false;
                if (!this.scope.isDestroyed()) {
                    this.restartCamera();
                }
            }
        }
    }

    restartCamera() {
        this.stopCamera();
        this.enableCamera();
    }

    stopCamera() {
        closeStream(this.state.videoStream);
        this.state.videoStream = null;
        this.cancelBlur();
    }
}
