const SUPPORTED_DOMAINS = [
    "youtu.be",
    "youtube.com",
    "youtube-nocookie.com",
    "instagram.com",
    "player.vimeo.com",
    "vimeo.com",
    "dailymotion.com",
];

/**
 * This is a non-lazy version of the `manageIframeSrc` function already
 * available in the `"website_cookies"` service. It was added here to
 * adapt video iframe `src` as soon as the HTML document is loaded,
 * (before interactions start), so that the iframes can be properly
 * displayed. Remark: the lazy-loaded code should use the function
 * from the `website_cookies` service.
 *
 * @param {HTMLIFrameElement} iframeEl
 * @param {string} src
 */
function manageIframeSrcOnLoad(iframeEl, src) {
    if (!iframeEl.closest("[data-need-cookies-approval]")) {
        iframeEl.setAttribute("src", src);
    } else {
        iframeEl.dataset.nocookieSrc = src;
        iframeEl.setAttribute("src", "about:blank");
        iframeEl.dataset.needCookiesApproval = "true";
    }
}

/**
 * Builds a video iframe for a saved `src` and appends it to the DOM.
 *
 * @param {HTMLElement} parentEl The iframe container.
 * @param {function} manageIframeSrcFct The iframe `src` handler.
 * @returns {HTMLIframeElement}
 */
export function generateVideoIframe(parentEl, manageIframeSrcFct) {
    // Bug fix / compatibility: empty the <div/> element as all information
    // to rebuild the iframe should have been saved on the <div/> element
    parentEl.replaceChildren();

    // Add extra content for size / edition
    const extraEditionEl = document.createElement("div");
    extraEditionEl.className = "css_editable_mode_display";
    const extraSizeEl = document.createElement("div");
    extraSizeEl.className = "media_iframe_video_size";
    parentEl.append(extraEditionEl, extraSizeEl);

    // Rebuild the iframe. Depending on version / compatibility / instance, the
    // src is saved in the 'data-src' attribute or the 'data-oe-expression' one.
    const src = parentEl.dataset.oeExpression || parentEl.dataset.src;
    // Validate the src to only accept supported domains we can trust
    const m = src.match(/^(?:https?:)?\/\/([^/?#]+)/);
    if (!m) {
        // Unsupported protocol or wrong URL format, don't inject iframe
        return;
    }
    const domain = m[1].replace(/^www\./, "");
    if (!SUPPORTED_DOMAINS.includes(domain)) {
        // Unsupported domain, don't inject iframe
        return;
    }
    const iframeEl = document.createElement("iframe");
    iframeEl.setAttribute("frameborder", "0");
    iframeEl.setAttribute("allowfullscreen", "allowfullscreen");
    iframeEl.setAttribute("referrerpolicy", "strict-origin-when-cross-origin");
    parentEl.appendChild(iframeEl);
    manageIframeSrcFct ? manageIframeSrcFct(iframeEl, src) : manageIframeSrcOnLoad(iframeEl, src);

    return iframeEl;
}

/**
 * Auto generate video iframes.
 */
document.addEventListener("DOMContentLoaded", () => {
    for (const videoIframeEl of document.querySelectorAll(".media_iframe_video")) {
        if (!videoIframeEl.querySelector(":scope > iframe")) {
            generateVideoIframe(videoIframeEl);
        }
    }
});
