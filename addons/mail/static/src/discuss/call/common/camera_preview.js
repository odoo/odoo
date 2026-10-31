import { CameraPreviewPlugin } from "@mail/discuss/call/common/camera_preview_plugin";

import {
    Component,
    onMounted,
    onWillDestroy,
    signal,
    types,
    useOnChange,
    usePlugin,
    useProps,
} from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class CameraPreview extends Component {
    static template = "discuss.CameraPreview";

    videoRef = signal.ref();

    setup() {
        this.props = useProps({
            onCameraStateChange: types.function([types.boolean()]).optional(() => () => {}),
        });
        this.cameraPreview = usePlugin(CameraPreviewPlugin);
        this.rtc = useService("discuss.rtc");
        this.state = this.cameraPreview.state;
        this.cameraPreviewAcquired = false;
        this.isMounted = false;
        this.lastCameraErrorCount = this.state.cameraErrorCount;
        onMounted(() => {
            this.isMounted = true;
            if (this.rtc.sourceCameraStream) {
                this.props.onCameraStateChange(true);
                return;
            }
            this.acquirePreview();
            if (this.state.videoStream) {
                this.props.onCameraStateChange(true);
            }
        });
        onWillDestroy(() => this.releasePreview());
        useOnChange(
            () => [
                this.videoRef(),
                this.state.videoStream,
                this.state.blurStream,
                this.rtc.sourceCameraStream,
                this.rtc.blurManager,
            ],
            () => this.assignStreamToVideoEl()
        );
        useOnChange(
            () => [this.rtc.sourceCameraStream],
            (sourceCameraStream) => {
                if (sourceCameraStream) {
                    this.releasePreview();
                    this.props.onCameraStateChange(true);
                } else if (this.isMounted) {
                    this.acquirePreview();
                }
            },
            { initialRun: false }
        );
        useOnChange(
            () => [this.state.videoStream, this.state.cameraErrorCount],
            (videoStream, cameraErrorCount) => {
                if (videoStream) {
                    this.props.onCameraStateChange(true);
                } else if (cameraErrorCount > this.lastCameraErrorCount) {
                    this.props.onCameraStateChange(false);
                }
                this.lastCameraErrorCount = cameraErrorCount;
            },
            { initialRun: false }
        );
    }

    acquirePreview() {
        if (!this.cameraPreviewAcquired) {
            this.cameraPreview.acquire();
            this.cameraPreviewAcquired = true;
        }
    }

    releasePreview() {
        if (this.cameraPreviewAcquired) {
            this.cameraPreview.release();
            this.cameraPreviewAcquired = false;
        }
    }

    async assignStreamToVideoEl() {
        const videoEl = this.videoRef();
        if (!videoEl) {
            return;
        }
        const sourceCameraStream = this.rtc.sourceCameraStream;
        const blurManager = this.rtc.blurManager;
        let callBlurStream;
        if (sourceCameraStream && blurManager) {
            try {
                callBlurStream = await blurManager.stream;
            } catch {
                // Fall back to the source stream if blur processing fails.
            }
        }
        if (videoEl !== this.videoRef()) {
            return;
        }
        const currentCallBlurStream =
            sourceCameraStream === this.rtc.sourceCameraStream &&
            blurManager === this.rtc.blurManager
                ? callBlurStream
                : null;
        videoEl.srcObject =
            currentCallBlurStream ??
            this.state.blurStream ??
            this.rtc.sourceCameraStream ??
            this.state.videoStream ??
            null;
    }
}
