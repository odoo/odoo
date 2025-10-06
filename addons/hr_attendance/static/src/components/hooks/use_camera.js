import { onWillUnmount } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export function useCamera({ width = 480, height = 480 } = {}) {
    const notification = useService("notification");
    let stream = null;
    let videoEl = null;

    async function start() {
        if (stream) {
            return stream;
        }

        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: width },
                    height: { ideal: height },
                },
                audio: false,
            });
            return stream;
        } catch (error) {
            notification.add(error.message || _t("Unable to access camera"), {
                title: _t("Camera Error"),
                type: "warning",
            });
            return null;
        }
    }

    function isStreamAvailable() {
        return !!stream;
    }

    async function attachStreamToVideo(el) {
        videoEl = el;
        if (videoEl && stream) {
            videoEl.srcObject = stream;
            await videoEl.play();
        }
    }

    function capturePicture() {
        if (!videoEl || !stream) {
            return null;
        }

        const canvas = document.createElement("canvas");
        canvas.width = videoEl.videoWidth;
        canvas.height = videoEl.videoHeight;

        const ctx = canvas.getContext("2d");
        ctx.drawImage(videoEl, 0, 0);

        return canvas.toDataURL("image/webp", 0.8).split(",")[1];
    }

    function stop() {
        stream?.getTracks().forEach((track) => track.stop());
        stream = null;
    }

    onWillUnmount(stop);

    return {
        start,
        isStreamAvailable,
        attachStreamToVideo,
        capturePicture,
        stop,
    };
}
