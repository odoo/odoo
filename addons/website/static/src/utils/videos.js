import { loadJS } from "@web/core/assets";
import { hasTouch } from "@web/core/browser/feature_detection";
import { SIZES, utils as uiUtils } from "@web/core/ui/ui_service";

/**
 * Takes care of any necessary setup for autoplaying video. In practice,
 * this method will load the youtube iframe API for mobile environments
 * because mobile environments don't support the youtube autoplay param
 * passed in the url.
 *
 * @param {string} src
 * @param {boolean} needCookiesApproval
 */
export function setupAutoplay(src, needCookiesApproval = false) {
    const isYoutubeVideo = src.indexOf("youtube") >= 0;
    const isMobileEnv = uiUtils.getSize() <= SIZES.LG && hasTouch();

    if (isYoutubeVideo && isMobileEnv && !window.YT && !needCookiesApproval) {
        const oldOnYoutubeIframeAPIReady = window.onYouTubeIframeAPIReady;
        const promise = new Promise((resolve) => {
            window.onYouTubeIframeAPIReady = () => {
                if (oldOnYoutubeIframeAPIReady) {
                    oldOnYoutubeIframeAPIReady();
                }
                return resolve();
            };
        });
        loadJS("https://www.youtube.com/iframe_api");
        return promise;
    }
    return Promise.resolve();
}

/**
 * @param {HTMLIframeElement} iframeEl - the iframe containing the video player
 */
export function triggerAutoplay(iframeEl) {
    const isYoutubeVideo = iframeEl.src.indexOf("youtube") >= 0;
    const isMobileEnv = uiUtils.getSize() <= SIZES.LG && hasTouch();

    // YouTube does not allow to auto-play video in mobile devices, so we
    // have to play the video manually.
    if (isYoutubeVideo && isMobileEnv && iframeEl.closest("[data-need-cookies-approval]")) {
        new window.YT.Player(iframeEl, {
            events: {
                onReady: (ev) => ev.target.playVideo(),
            },
        });
    }
}
