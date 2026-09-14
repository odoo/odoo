/** @odoo-module native */
import { makeLogger } from "@web/core/debug/debug_logger";
import { isSupportedVideoUrl, parseVideoUrl } from "@website/utils/video_urls";

const log = makeLogger("website.content.generate_video_iframe");

/** @param {HTMLElement} el */
export function isVideoInClosedPopup(el) {
    return !!el.closest(".s_popup .modal:not(.show)");
}

/**
 * @param {HTMLIFrameElement} iframeEl
 * @param {string} src
 */
function manageIframeSrcOnLoad(iframeEl, src) {
    if (!iframeEl.closest("[data-need-cookies-approval]")) {
        iframeEl.setAttribute("src", src);
    } else {
        log.logic("iframe src held until cookies approval", () => ({ src }));
        iframeEl.dataset.nocookieSrc = src;
        iframeEl.setAttribute("src", "about:blank");
        iframeEl.dataset.needCookiesApproval = "true";
    }
}

/**
 * @param {HTMLElement} parentEl
 * @param {function} [manageIframeSrcFct]
 * @returns {HTMLIframeElement}
 */
export function generateVideoIframe(parentEl, manageIframeSrcFct) {
    const src = parentEl.dataset.oeExpression || parentEl.dataset.src;
    const url = parseVideoUrl(src);
    if (!isSupportedVideoUrl(url)) {
        log.logic("skip: unsupported or incomplete video URL", () => ({ src }));
        return;
    }
    parentEl.replaceChildren();
    const extraEditionEl = document.createElement("div");
    extraEditionEl.className = "css_editable_mode_display";
    const extraSizeEl = document.createElement("div");
    extraSizeEl.className = "media_iframe_video_size";
    parentEl.append(extraEditionEl, extraSizeEl);

    const iframeEl = document.createElement("iframe");
    iframeEl.setAttribute("frameborder", "0");
    iframeEl.setAttribute("allowfullscreen", "allowfullscreen");
    iframeEl.setAttribute("referrerpolicy", "strict-origin-when-cross-origin");
    parentEl.appendChild(iframeEl);
    log.pipeline("video iframe created", () => ({
        domain: url.hostname,
        customSrcManager: !!manageIframeSrcFct,
    }));
    if (isVideoInClosedPopup(parentEl)) {
        // A consent event must not load a popup that has never been opened.
        iframeEl.setAttribute("src", "about:blank");
        log.lifecycle("video source deferred until popup opening");
    } else {
        manageIframeSrcFct
            ? manageIframeSrcFct(iframeEl, src)
            : manageIframeSrcOnLoad(iframeEl, src);
    }

    return iframeEl;
}

document.addEventListener("DOMContentLoaded", () => {
    log.pipeline("DOMContentLoaded video placeholders", () => ({
        placeholders: document.querySelectorAll(".media_iframe_video").length,
    }));
    for (const videoIframeEl of document.querySelectorAll(".media_iframe_video")) {
        if (!videoIframeEl.querySelector(":scope > iframe")) {
            generateVideoIframe(videoIframeEl);
        }
    }
});
