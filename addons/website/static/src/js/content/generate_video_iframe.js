import { Youtube } from "@html_editor/main/media/video/providers/youtube";
import { Dailymotion } from "@html_editor/main/media/video/providers/dailymotion";
import { Vimeo } from "@html_editor/main/media/video/providers/vimeo";
import { GDriveVideo } from "@html_editor/main/media/video/providers/gdrive_video";
import { Instagram } from "@html_editor/main/media/video/providers/instagram";
import { Facebook } from "@html_editor/main/media/video/providers/facebook";
import { Twitch } from "@html_editor/main/media/video/providers/twitch";
import { Loom } from "@html_editor/main/media/video/providers/loom";

export const PLATFORMS = {
    youtube: Youtube,
    instagram: Instagram,
    facebook: Facebook,
    gDrive: GDriveVideo,
    dailymotion: Dailymotion,
    vimeo: Vimeo,
    twitch: Twitch,
    loom: Loom,
};

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
 * @returns {HTMLIFrameElement}
 */
export function generateVideoIframe(parentEl, manageIframeSrcFct) {
    // Depending on version / compatibility / instance, the src is saved in the
    // 'data-embed-url', 'data-src' attribute or the 'data-oe-expression' one.
    let src = parentEl.dataset.embedUrl || parentEl.dataset.src || parentEl.dataset.oeExpression;
    // Do not generate an iframe if there is no src, as it means that the
    // container only contains the SVG placeholder.
    if (!src) {
        return;
    }

    // Bug fix / compatibility: empty the <div/> element as all information
    // to rebuild the iframe should have been saved on the <div/> element
    parentEl.replaceChildren();

    // Add extra content for size / edition
    const extraEditionEl = document.createElement("div");
    extraEditionEl.className = "css_editable_mode_display";
    const extraSizeEl = document.createElement("div");
    extraSizeEl.className = parentEl.dataset.isVertical
        ? "media_iframe_video_size_for_vertical"
        : "media_iframe_video_size";
    parentEl.append(extraEditionEl, extraSizeEl);

    // Deprecated oeExpression store the src without protocol for some reason.
    if (src.startsWith("//")) {
        src = "https:" + src;
    }

    if (!URL.canParse(src)) {
        // not a valid URL, don't inject iframe
        return null;
    }
    // Check if the url is from one of the supported platforms.
    let platform = false;
    let urlMatch;
    for (const [p, pClass] of Object.entries(PLATFORMS)) {
        urlMatch = pClass.isValidVideoUrl(src);
        if (urlMatch) {
            platform = p;
            break;
        }
    }
    if (!platform) {
        return null;
    }
    // Sanitize the URL by processing it back into the platform matcher.
    src = PLATFORMS[platform].getVideoUrlData(urlMatch).embedUrl;

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
