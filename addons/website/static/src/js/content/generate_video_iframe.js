/** @odoo-module **/

/**
 * Escapes a string to HTML interpolation.
 * Remark: this function is already available in the codebase (see:
 * `web/.../code/utils/strings.js`) and from `underscore.js`, but we need to
 * reimplement it here for non-lazy code.
 *
 * @param {string} str The string to escape.
 * @returns {string}
 */
export function escape(str) {
    if (!str) {
        return "";
    }
    for (const [unescaped, escaped] of [
        ["&", "&amp;"],
        ["<", "&lt;"],
        [">", "&gt;"],
        ["'", "&#x27;"],
        ['"', "&quot;"],
        ["`", "&#x60;"],
    ]) {
        str = str.replaceAll(unescaped, escaped);
    }
    return str;
}

/**
 * Builds a video iframe for a saved `src` and appends it to the DOM.
 *
 * @param {HTMLElement} parentEl The iframe container.
 * @returns {HTMLIframeElement}
 */
export function generateVideoIframe(parentEl) {
    // Bug fix / compatibility: empty the <div/> element as all information
    // to rebuild the iframe should have been saved on the <div/> element
    parentEl.replaceChildren();

    // Add extra content for size / edition
    const extraEditionEl = document.createElement("div");
    extraEditionEl.className = "css_editable_mode_display";
    const extraSizeEl = document.createElement("div");
    extraSizeEl.className = "media_iframe_video_size";
    parentEl.append(extraEditionEl, extraSizeEl);

    // Rebuild the iframe. Depending on version / compatibility / instance,
    // the src is saved in the 'data-src' attribute or the
    // 'data-oe-expression' one (the latter is used as a workaround in 10.0
    // system but should obviously be reviewed in master).
    const src = escape(parentEl.dataset.oeExpression || parentEl.dataset.src);
    // Validate the src to only accept supported domains we can trust
    var m = src.match(/^(?:https?:)?\/\/([^/?#]+)/);
    if (!m) {
        // Unsupported protocol or wrong URL format, don't inject iframe
        return;
    }
    var domain = m[1].replace(/^www\./, '');
    var supportedDomains = ['youtu.be', 'youtube.com', 'youtube-nocookie.com', 'instagram.com', 'vine.co', 'player.vimeo.com', 'vimeo.com', 'dailymotion.com', 'player.youku.com', 'youku.com'];
    if (!supportedDomains.includes(domain)) {
        // Unsupported domain, don't inject iframe
        return;
    }
    const iframeEl = document.createElement("iframe");
    iframeEl.setAttribute("src", src);
    iframeEl.setAttribute("frameborder", "0");
    iframeEl.setAttribute("allowfullscreen", "allowfullscreen");
    parentEl.appendChild(iframeEl);

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
