import { StorePlugin } from "@mail/core/common/store_plugin";
import { closeStream } from "@mail/utils/common/misc";

import { onWillDestroy, Plugin, proxy, toRaw, useOnChange, usePlugin } from "@odoo/owl";

import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { services } from "@web/core/services";

export class CameraPreviewPlugin extends Plugin {
    /**
     * The CameraPreviewPlugin depends on NotificationPlugin and StorePlugin.
     * Start it after both.
     */
    static sequence = 120;

    notification = usePlugin(NotificationPlugin);
    store = usePlugin(StorePlugin);
    state = proxy({
        blurManager: null,
        blurRequestId: 0,
        blurStream: null,
        cameraRequestId: 0,
        cameraErrorCount: 0,
        isEnablingCamera: false,
        isRestartQueued: false,
        videoStream: null,
    });

    setup() {
        this.rtc = this.store.rtc;
        this.consumerCount = 0;
        useOnChange(
            () => [this.rtc.cameraPermission],
            (cameraPermission) => {
                if (cameraPermission !== "granted" && this.consumerCount) {
                    this.failCamera();
                } else if (
                    cameraPermission === "granted" &&
                    this.consumerCount &&
                    !this.state.videoStream
                ) {
                    this.enableCamera();
                }
            },
            { initialRun: false }
        );
        useOnChange(
            () => [this.store.settings.cameraInputDeviceId],
            () => {
                if (!this.consumerCount) {
                    return;
                }
                if (this.state.isEnablingCamera) {
                    this.state.isRestartQueued = true;
                } else if (this.state.videoStream) {
                    this.restartCamera();
                }
            },
            { initialRun: false }
        );
        useOnChange(
            () => [this.store.settings.useBlur],
            (useBlur) => {
                if (!this.consumerCount || !this.state.videoStream) {
                    return;
                }
                if (useBlur) {
                    this.enableBlur();
                } else {
                    this.cancelBlur();
                }
            },
            { initialRun: false }
        );
        useOnChange(
            () => [this.store.settings.edgeBlurAmount, this.store.settings.backgroundBlurAmount],
            (edgeBlurAmount, backgroundBlurAmount) => {
                if (this.state.blurManager) {
                    this.state.blurManager.edgeBlur = edgeBlurAmount;
                    this.state.blurManager.backgroundBlur = backgroundBlurAmount;
                }
            },
            { initialRun: false }
        );
        onWillDestroy(() => this.stopPreviewCapture());
    }

    acquire() {
        this.consumerCount++;
        if (this.state.videoStream) {
            return;
        }
        if (this.state.isEnablingCamera) {
            if (this.consumerCount === 1) {
                this.state.isRestartQueued = true;
            }
            return;
        }
        this.enableCamera();
    }

    release() {
        if (!this.consumerCount) {
            return;
        }
        this.consumerCount--;
        if (!this.consumerCount) {
            this.state.isRestartQueued = false;
            this.stopPreviewCapture();
        }
    }

    cancelBlur() {
        this.state.blurRequestId++;
        this.state.blurManager?.close();
        this.state.blurManager = null;
        this.state.blurStream = null;
    }

    stopPreviewCapture() {
        this.state.cameraRequestId++;
        closeStream(this.state.videoStream);
        this.state.videoStream = null;
        this.cancelBlur();
    }

    failCamera() {
        this.state.isRestartQueued = false;
        this.stopPreviewCapture();
        this.state.cameraErrorCount++;
    }

    async enableBlur() {
        const videoStream = this.state.videoStream;
        if (!videoStream || this.state.blurManager) {
            return;
        }
        const requestId = ++this.state.blurRequestId;
        const isStale = () => !this.consumerCount || requestId !== this.state.blurRequestId;
        let blurManager;
        try {
            blurManager = this.rtc.applyBlurEffect(videoStream);
            this.state.blurManager?.close();
            this.state.blurManager = blurManager;
            const blurStream = await blurManager.stream;
            if (isStale()) {
                if (toRaw(this.state.blurManager) === blurManager) {
                    this.state.blurManager = null;
                    blurManager.close();
                }
                return;
            }
            this.state.blurStream = blurStream;
        } catch (error) {
            if (toRaw(this.state.blurManager) === blurManager) {
                this.state.blurManager = null;
                blurManager.close();
            }
            if (isStale()) {
                return;
            }
            this.notification.add(error.message, { type: "warning" });
            if (!this.state.blurManager) {
                this.store.settings.useBlur = false;
            }
        }
    }

    async enableCamera() {
        if (this.state.videoStream || this.state.isEnablingCamera || !this.consumerCount) {
            return;
        }
        this.state.isEnablingCamera = true;
        const requestId = ++this.state.cameraRequestId;
        try {
            const hasPermission =
                this.rtc.cameraPermission === "granted" ||
                (await this.rtc.askForBrowserPermission({ video: true }));
            if (!this.consumerCount || requestId !== this.state.cameraRequestId) {
                return;
            }
            if (!hasPermission) {
                this.failCamera();
                return;
            }
            const cameraInputDeviceId = this.store.settings.cameraInputDeviceId;
            const stream = await navigator.mediaDevices.getUserMedia({
                video: this.store.settings.cameraConstraints,
            });
            if (
                !this.consumerCount ||
                requestId !== this.state.cameraRequestId ||
                this.store.settings.cameraInputDeviceId !== cameraInputDeviceId
            ) {
                closeStream(stream);
                if (this.consumerCount && requestId === this.state.cameraRequestId) {
                    this.state.isRestartQueued = true;
                }
                return;
            }
            this.state.videoStream = stream;
            if (this.store.settings.useBlur) {
                await this.enableBlur();
            }
        } catch {
            if (
                this.consumerCount &&
                requestId === this.state.cameraRequestId &&
                !this.state.isRestartQueued
            ) {
                this.failCamera();
            }
        } finally {
            this.state.isEnablingCamera = false;
            const isRestartQueued = this.state.isRestartQueued;
            this.state.isRestartQueued = false;
            if (isRestartQueued && this.consumerCount) {
                this.restartCamera();
            }
        }
    }

    restartCamera() {
        this.stopPreviewCapture();
        this.enableCamera();
    }
}

services.add(CameraPreviewPlugin);
