import { browser } from "@web/core/browser/browser";
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
            stream = await browser.navigator.mediaDevices.getUserMedia({
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

    function isWebPSupported() {
        const canvas = document.createElement("canvas");
        return canvas.toDataURL("image/webp").slice(0, 15) === "data:image/webp";
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
        const [mimetype, compression] = isWebPSupported()
            ? ["image/webp", 0.8]
            : ["image/jpeg", 0.6];
        return canvas.toDataURL(mimetype, compression);
    }

    function stop() {
        stream?.getTracks().forEach((track) => track.stop());
        stream = null;
    }

    return {
        start,
        isStreamAvailable,
        attachStreamToVideo,
        capturePicture,
        stop,
    };
}
