import { browser } from "@web/core/browser/browser";

export const DESKTOP_PREVIEW_WIDTH = 1440;

/**
 * Build the URL rendering a static preview with the current configurator
 * selection (palette, industry images, dark mode).
 *
 * @param {Object} state configurator store
 * @param {string} previewUrl local path of the static preview HTML
 * @param {string} [themeName]
 * @returns {string}
 */
export function getConfiguratorPreviewUrl(state, previewUrl, themeName = "") {
    const url = new URL("/website/configurator/preview", browser.location.origin);
    const palette = state.selectedPalette || {};
    url.searchParams.set("preview_url", previewUrl);
    url.searchParams.set("theme_name", themeName);
    url.searchParams.set("industry_id", state.selectedIndustry?.id || -1);
    url.searchParams.set("is_dark", palette.isDark ? "1" : "0");
    for (const colorName of ["color1", "color2", "color3", "color4", "color5"]) {
        url.searchParams.set(colorName, palette[colorName] || "");
    }
    return url.toString();
}

export function getPreviewIframeDocument(iframe) {
    try {
        const previewDocument = iframe.contentDocument;
        return previewDocument?.readyState === "complete" ? previewDocument : null;
    } catch (error) {
        if (error.name === "SecurityError") {
            return null;
        }
        throw error;
    }
}

export function replacePreviewIframeLogo(iframe, logo) {
    if (!logo) {
        return;
    }
    const previewDocument = getPreviewIframeDocument(iframe);
    if (!previewDocument) {
        return;
    }
    const logoImage = previewDocument.querySelector("header img, #top img, .navbar-brand img");
    if (logoImage) {
        logoImage.src = logo;
    }
}

function getPreviewIframeContentSize(iframe) {
    const iframeWindow = iframe.contentWindow;
    const iframeDocument = getPreviewIframeDocument(iframe);
    const scrollingElement = iframeDocument?.scrollingElement;
    const documentElement = iframeDocument?.documentElement;
    const body = iframeDocument?.body;
    if (!iframeWindow || !scrollingElement || !documentElement) {
        return null;
    }
    return {
        width: Math.max(
            DESKTOP_PREVIEW_WIDTH,
            iframeWindow.innerWidth,
            scrollingElement.scrollWidth,
            documentElement.scrollWidth,
            body?.scrollWidth || 0
        ),
        height: Math.max(
            scrollingElement.scrollHeight,
            documentElement.scrollHeight,
            body?.scrollHeight || 0,
            documentElement.offsetHeight,
            body?.offsetHeight || 0
        ),
    };
}

export function scalePreviewIframe(iframe) {
    if (!iframe) {
        return;
    }

    const previewContainer = iframe.parentElement;
    const availableWidth = previewContainer.clientWidth;
    const availableHeight = previewContainer.clientHeight;

    if (!availableWidth || !availableHeight) {
        return;
    }

    iframe.style.setProperty("width", `${DESKTOP_PREVIEW_WIDTH}px`, "important");
    // Reset to the natural viewport height before measuring
    const naturalViewportHeight = Math.ceil(
        availableHeight / Math.min(1, availableWidth / DESKTOP_PREVIEW_WIDTH)
    );
    iframe.style.setProperty("height", `${naturalViewportHeight}px`, "important");

    const contentSize = getPreviewIframeContentSize(iframe);
    const iframeWidth = contentSize?.width || DESKTOP_PREVIEW_WIDTH;
    const scale = Math.min(1, availableWidth / iframeWidth);
    const fallbackContentHeight = (availableHeight * 2) / scale;
    const iframeHeight = Math.ceil(contentSize?.height || fallbackContentHeight);
    // The iframe is scaled, so the scroll distance must use the scaled
    // height, not the raw document height.
    const scrollDistance = Math.max(0, iframeHeight * scale - availableHeight);

    iframe.style.setProperty("width", `${iframeWidth}px`, "important");
    iframe.style.setProperty("height", `${iframeHeight}px`, "important");
    iframe.style.setProperty(
        "--o-configurator-iframe-scroll-distance",
        `${Math.floor(scrollDistance)}px`
    );
    iframe.style.setProperty("--o-configurator-iframe-scale", scale);
    iframe.style.setProperty("transform-origin", "top left");
    iframe.style.setProperty("flex", "0 0 auto", "important");
}
