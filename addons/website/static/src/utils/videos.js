/** @odoo-module native */
import { loadJS } from "@web/core/assets";
import { hasTouch } from "@web/core/browser/feature_detection";
import { makeLogger } from "@web/core/debug/debug_logger";
import { SIZES, utils as uiUtils } from "@web/ui/viewport";
import { isYoutubeUrl, parseVideoUrl } from "@website/utils/video_urls";

const log = makeLogger("website.utils.videos");

let youtubeAPILoading;

/** Wait for both the script download and the provider's readiness callback. */
function loadYoutubeAPI() {
    if (!youtubeAPILoading) {
        const previousCallback = window.onYouTubeIframeAPIReady;
        let onReady;
        const ready = new Promise((resolve) => {
            onReady = () => {
                log.lifecycle("youtube iframe api ready");
                resolve();
                try {
                    previousCallback?.();
                } catch (error) {
                    log.logic("youtube previous ready callback failed", () => ({
                        error,
                    }));
                }
            };
            window.onYouTubeIframeAPIReady = onReady;
        });
        youtubeAPILoading = Promise.resolve()
            .then(() =>
                Promise.all([loadJS("https://www.youtube.com/iframe_api"), ready]),
            )
            .catch((error) => {
                // Native iframe playback remains available; a later video can
                // retry the optional API instead of inheriting a stuck promise.
                log.logic("youtube iframe api failed, allow retry", () => ({ error }));
            })
            .finally(() => {
                if (window.onYouTubeIframeAPIReady === onReady) {
                    if (previousCallback === undefined) {
                        delete window.onYouTubeIframeAPIReady;
                    } else {
                        window.onYouTubeIframeAPIReady = previousCallback;
                    }
                }
                youtubeAPILoading = undefined;
            });
    }
    return youtubeAPILoading;
}

/**
 * @param {string} src
 * @param {boolean} needCookiesApproval
 */
export function setupAutoplay(src, needCookiesApproval = false) {
    const isYoutubeVideo = isYoutubeUrl(parseVideoUrl(src));
    const isMobileEnv = uiUtils.getSize() <= SIZES.LG && hasTouch();
    const isReady = typeof window.YT?.Player === "function";

    log.logic("setupAutoplay", () => ({
        isYoutubeVideo,
        isMobileEnv,
        isReady,
        needCookiesApproval,
    }));
    if (isYoutubeVideo && isMobileEnv && !isReady && !needCookiesApproval) {
        log.pipeline("setupAutoplay: loading youtube iframe api");
        return loadYoutubeAPI();
    }
    return Promise.resolve();
}

/**
 * @param {HTMLIFrameElement} iframeEl
 * @param {() => boolean} [canPlay] Rechecked when the player becomes ready.
 */
export function triggerAutoplay(iframeEl, canPlay = () => true) {
    const isYoutubeVideo = isYoutubeUrl(parseVideoUrl(iframeEl.src));
    const isMobileEnv = uiUtils.getSize() <= SIZES.LG && hasTouch();

    if (
        isYoutubeVideo &&
        isMobileEnv &&
        !iframeEl.closest("[data-need-cookies-approval]") &&
        typeof window.YT?.Player === "function" &&
        canPlay()
    ) {
        log.lifecycle("triggerAutoplay: creating YT player", () => ({
            src: iframeEl.src,
        }));
        new window.YT.Player(iframeEl, {
            events: {
                onReady: (ev) => {
                    if (canPlay()) {
                        ev.target.playVideo();
                    } else {
                        log.lifecycle(
                            "player ready after its autoplay request expired",
                        );
                    }
                },
            },
        });
    }
}
