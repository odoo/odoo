import { getBgImageURLFromEl } from "@html_builder/utils/utils_css";
import { MEDIAS_BREAKPOINTS, SIZES } from "@web/core/ui/ui_utils";
import { delay } from "@web/core/utils/concurrency";

/**
 * @typedef {{ width: number, height: number }} LcpViewport
 */

const DESKTOP_LCP_VIEWPORT_WIDTH = MEDIAS_BREAKPOINTS[SIZES["LG"]]["maxWidth"];
const MOBILE_LCP_VIEWPORT_WIDTH = MEDIAS_BREAKPOINTS[SIZES["MD"]]["maxWidth"];

const DESKTOP_LCP_VIEWPORT_SIZE = {
    width: DESKTOP_LCP_VIEWPORT_WIDTH,
    height: Math.round(DESKTOP_LCP_VIEWPORT_WIDTH * 0.5626), // aspect ratio (16:9)
};

const MOBILE_LCP_VIEWPORT_SIZE = {
    width: MOBILE_LCP_VIEWPORT_WIDTH,
    height: Math.round(MOBILE_LCP_VIEWPORT_WIDTH * 1.7777), // aspect ratio (9:16)
};

const LCP_QUIET_DELAY = 200;
const LCP_OBSERVE_TIMEOUT = 2000;

export const lcpMeasurement = {
    /**
     * @param {Document} pageDocument the rendered page
     * @returns {Promise<Object>}
     */
    async measureLcpImages(pageDocument) {
        const [desktopUrl, mobileUrl] = await Promise.all([
            this.electImageUrl(DESKTOP_LCP_VIEWPORT_SIZE, pageDocument),
            this.electImageUrl(MOBILE_LCP_VIEWPORT_SIZE, pageDocument),
        ]);
        const values = {};
        if (desktopUrl !== undefined) {
            values.website_lcp_image_desktop = desktopUrl;
        }
        if (mobileUrl !== undefined) {
            values.website_lcp_image_mobile = mobileUrl;
        }
        return values;
    },

    /**
     * @param {LcpViewport} viewportSize
     * @param {Document} pageDocument
     * @returns {Promise<string | false | null | undefined>}
     */
    async electImageUrl(viewportSize, pageDocument) {
        const { hostEl, measurementIframeEl } = await this.appendMeasureFrame(viewportSize);
        try {
            const measureDocument = measurementIframeEl.contentDocument;
            const styleSheetsSettled = this.fillMeasurementDocument(measureDocument, pageDocument);
            await this.waitForMeasurementResources(measureDocument, styleSheetsSettled);
            const entryEl = await this.observeLcpEntry(measureDocument.defaultView);
            return entryEl && this.imageUrl(entryEl);
        } finally {
            hostEl.remove();
        }
    },

    /**
     * @param {Element} entryEl the element of the largest contentful paint entry
     * @returns {string | false}
     */
    imageUrl(entryEl) {
        let source;
        switch (entryEl.tagName) {
            case "IMG":
                source = entryEl.getAttribute("src");
                break;
            default:
                source = getBgImageURLFromEl(entryEl);
        }
        if (!source) {
            return false;
        }
        // Inline sources (data:, blob:) cannot be preloaded by `<link>`.
        const { origin } = window.location;
        const url = new URL(source, origin);
        if (!["http:", "https:"].includes(url.protocol)) {
            return false;
        }
        // Same-origin images are stored as a path so that the hint survives a
        // domain change and goes through the usual CDN rewriting at render
        // time. External images keep their absolute URL.
        return url.origin === origin ? url.pathname + url.search : url.href;
    },

    /**
     * @param {LcpViewport} viewportSize
     * @returns {Promise<{ hostEl: HTMLDivElement, measurementIframeEl: HTMLIFrameElement }>}
     */
    async appendMeasureFrame(viewportSize) {
        const hostEl = document.createElement("div");
        hostEl.setAttribute("aria-hidden", "true");
        const scale = this.measurementScale(viewportSize);
        hostEl.style.cssText =
            "position: fixed; top: 0; left: 0; pointer-events: none; filter: opacity(0);" +
            `transform: scale(${scale}); transform-origin: 0 0;`;
        const measurementIframeEl = document.createElement("iframe");
        measurementIframeEl.style.cssText = `border: 0; width: ${viewportSize.width}px; height: ${viewportSize.height}px;`;
        hostEl.attachShadow({ mode: "closed" }).appendChild(measurementIframeEl);
        await new Promise((resolve) => {
            measurementIframeEl.addEventListener("load", resolve, { once: true });
            document.body.appendChild(hostEl);
        });
        return { hostEl, measurementIframeEl };
    },

    /**
     * @param {LcpViewport} viewportSize
     * @returns {number}
     */
    measurementScale(viewportSize) {
        return Math.min(
            1,
            window.innerWidth / viewportSize.width,
            window.innerHeight / viewportSize.height
        );
    },

    /**
     * @param {Document} measureDocument
     * @param {Document} pageDocument
     * @returns {Promise<void>[]} settles once each copied stylesheet has
     *   loaded or failed
     */
    fillMeasurementDocument(measureDocument, pageDocument) {
        this.copyAttributes(pageDocument.documentElement, measureDocument.documentElement);
        measureDocument.documentElement.classList.remove("o_is_mobile");
        this.copyAttributes(pageDocument.body, measureDocument.body);
        const styleSheetsSettled = [];
        for (const headEl of pageDocument.head.children) {
            if (headEl.tagName === "SCRIPT") {
                continue;
            }
            const headElClone = headEl.cloneNode(true);
            if (headElClone.matches("link[rel='stylesheet']")) {
                // Listen before insertion: a stylesheet that fails to load
                // fires `error` only once and keeps `sheet` null.
                styleSheetsSettled.push(
                    new Promise((resolve) => {
                        headElClone.addEventListener("load", resolve, { once: true });
                        headElClone.addEventListener("error", resolve, { once: true });
                    })
                );
            }
            measureDocument.head.appendChild(headElClone);
        }
        for (const bodyNode of pageDocument.body.childNodes) {
            if (bodyNode.tagName === "SCRIPT") {
                continue;
            }
            measureDocument.body.appendChild(bodyNode.cloneNode(true));
        }
        for (const imgEl of measureDocument.images) {
            imgEl.setAttribute("loading", "eager");
        }
        return styleSheetsSettled;
    },

    /**
     * @param {Element} sourceEl
     * @param {Element} targetEl
     * @returns {void}
     */
    copyAttributes(sourceEl, targetEl) {
        for (const { name, value } of sourceEl.attributes) {
            targetEl.setAttribute(name, value);
        }
    },

    /**
     * @param {Document} measureDocument
     * @param {Promise<void>[]} styleSheetsSettled
     * @returns {Promise<void>}
     */
    async waitForMeasurementResources(measureDocument, styleSheetsSettled) {
        await Promise.all([
            ...styleSheetsSettled,
            // The largest contentful paint entry is only final once every
            // image is painted; a failed image is simply never a candidate.
            ...[...measureDocument.images].map((imgEl) => imgEl.decode().catch(() => {})),
            measureDocument.fonts.ready,
        ]);
    },

    /**
     * @param {Window & typeof globalThis} win
     * @returns {Promise<Element | null | undefined>}
     */
    async observeLcpEntry(win) {
        const IframePerformanceObserver = win.PerformanceObserver;
        const entries = [];
        let notifyQuiet;
        let quietTimeout;
        const quiet = new Promise((resolve) => (notifyQuiet = resolve));
        const observer = new IframePerformanceObserver((entryList) => {
            entries.push(...entryList.getEntries());
            clearTimeout(quietTimeout);
            quietTimeout = setTimeout(notifyQuiet, LCP_QUIET_DELAY);
        });
        observer.observe({ type: "largest-contentful-paint", buffered: true });
        await Promise.race([quiet, delay(LCP_OBSERVE_TIMEOUT)]);
        clearTimeout(quietTimeout);
        entries.push(...observer.takeRecords());
        observer.disconnect();
        return entries.at(-1)?.element;
    },
};
