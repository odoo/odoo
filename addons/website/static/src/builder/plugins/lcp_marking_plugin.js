import { getBgImageURLFromEl } from "@html_builder/utils/utils_css";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { MEDIAS_BREAKPOINTS, SIZES } from "@web/core/ui/ui_utils";
import { delay } from "@web/core/utils/concurrency";

/**
 * @typedef {{ width: number, height: number }} LcpViewport
 * @typedef {{ editableCloneEl: HTMLElement, sourceDocument: Document }} LcpSnapshot
 * @typedef {{ model: string, id: number }} LcpRecord
 * @typedef {((measureDocument: Document) => void)[]} on_will_save_lcp_handlers
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

const IMAGE_FIELD_SRC_ATTRIBUTE = "data-lcp-image-field-src";
const LCP_QUIET_DELAY = 200;
const LCP_OBSERVE_TIMEOUT = 2000;

export class LcpMarkingPlugin extends Plugin {
    static id = "lcpMarking";
    resources = {
        clean_for_save_processors: this.cleanForSave.bind(this),
        on_ready_to_save_document_handlers: this.startLcpMeasurement.bind(this),
        on_will_save_media_dialog_handlers: this.preserveImageFieldSrc.bind(this),
        system_attributes: [IMAGE_FIELD_SRC_ATTRIBUTE],
    };

    /**
     * @returns {Promise<void>}
     */
    async startLcpMeasurement() {
        const record = this.lcpRecord();
        // Some users (e.g., event managers) can edit fields but cannot change
        // the `seo_object`. The modification of lcp data is avoided in such
        // scenarios
        if (!this.services.website.isDesigner) {
            return;
        }
        const snapshot = this.snapshotEditable();
        const canWrite = await this.services.orm.call(record.model, "has_access", [
            [record.id],
            "write",
        ]);
        if (!canWrite) {
            return;
        }
        return this.saveLcpImages(record, snapshot);
    }

    /**
     * @returns {LcpSnapshot}
     */
    snapshotEditable() {
        const editableCloneEl = this.editable.cloneNode(true);
        for (const imgEl of editableCloneEl.querySelectorAll("img")) {
            imgEl.setAttribute("loading", "eager");
        }
        return { editableCloneEl, sourceDocument: this.editable.ownerDocument };
    }

    /**
     * @param {LcpRecord} record
     * @param {LcpSnapshot} snapshot
     * @returns {Promise<void>}
     */
    async saveLcpImages(record, snapshot) {
        const [desktopUrl, mobileUrl] = await Promise.all([
            this.electImageUrl(DESKTOP_LCP_VIEWPORT_SIZE, snapshot),
            this.electImageUrl(MOBILE_LCP_VIEWPORT_SIZE, snapshot),
        ]);
        const values = {};
        if (desktopUrl !== undefined) {
            values.website_lcp_image_desktop = desktopUrl;
        }
        if (mobileUrl !== undefined) {
            values.website_lcp_image_mobile = mobileUrl;
        }
        if (!Object.keys(values).length) {
            return;
        }
        await this.services.orm.write(record.model, [record.id], values, {
            context: {
                lang: this.services.website.currentWebsite.metadata.lang,
                website_id: this.services.website.currentWebsite.id,
                no_cow: true,
            },
        });
    }

    /**
     * @returns {LcpRecord | null}
     */
    lcpRecord() {
        const metadata = this.services.website.currentWebsite.metadata;
        return metadata.seoObject || metadata.mainObject;
    }

    /**
     * @param {HTMLElement[]} elements
     * @param {{ node?: Node | null }} params
     * @returns {void}
     */
    preserveImageFieldSrc(elements, { node }) {
        if (!node?.parentElement?.matches("[data-oe-type='image']")) {
            return;
        }
        const source =
            node.getAttribute(IMAGE_FIELD_SRC_ATTRIBUTE) || node.getAttributeNode("src").value;
        for (const imageEl of elements) {
            imageEl.setAttribute(IMAGE_FIELD_SRC_ATTRIBUTE, source);
        }
    }

    /**
     * @param {HTMLElement} rootEl
     * @returns {HTMLElement}
     */
    cleanForSave(rootEl) {
        for (const imgEl of rootEl.querySelectorAll(`[${IMAGE_FIELD_SRC_ATTRIBUTE}]`)) {
            imgEl.removeAttribute(IMAGE_FIELD_SRC_ATTRIBUTE);
        }

        return rootEl;
    }

    /**
     * @param {LcpViewport} viewportSize
     * @param {LcpSnapshot} snapshot
     * @returns {Promise<string | false | undefined>}
     */
    async electImageUrl(viewportSize, snapshot) {
        const { hostEl, measurementIframeEl } = await this.appendMeasureFrame(viewportSize);
        try {
            const measureDocument = measurementIframeEl.contentDocument;
            const styleSheetsSettled = this.fillMeasurementDocument(measureDocument, snapshot);
            this.trigger("on_will_save_lcp_handlers", measureDocument);
            await this.waitForMeasurementResources(measureDocument, styleSheetsSettled);
            const entryEl = await this.observeLcpEntry(measureDocument.defaultView);
            return entryEl && this.imageUrl(entryEl);
        } finally {
            hostEl.remove();
        }
    }

    /**
     * @param {Element} entryEl the element of the largest contentful paint entry
     * @returns {string | false}
     */
    imageUrl(entryEl) {
        let source;
        switch (entryEl.tagName) {
            case "IMG":
                source =
                    entryEl.getAttribute(IMAGE_FIELD_SRC_ATTRIBUTE) || entryEl.getAttribute("src");
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
    }

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
    }

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
    }

    /**
     * @param {Document} measureDocument
     * @param {LcpSnapshot} snapshot
     * @returns {Promise<void>[]} settles once each copied stylesheet has
     *   loaded or failed
     */
    fillMeasurementDocument(measureDocument, { editableCloneEl, sourceDocument }) {
        this.copyAttributes(sourceDocument.documentElement, measureDocument.documentElement);
        measureDocument.documentElement.classList.remove("o_is_mobile");
        this.copyAttributes(sourceDocument.body, measureDocument.body);
        const styleSheetsSettled = [];
        for (const headNode of sourceDocument.head.childNodes) {
            if (headNode.tagName === "SCRIPT") {
                continue;
            }
            const headNodeClone = headNode.cloneNode(true);
            if (headNodeClone.matches?.("link[rel='stylesheet']")) {
                // Listen before insertion: a stylesheet that fails to load
                // fires `error` only once and keeps `sheet` null.
                styleSheetsSettled.push(
                    new Promise((resolve) => {
                        headNodeClone.addEventListener("load", resolve, { once: true });
                        headNodeClone.addEventListener("error", resolve, { once: true });
                    })
                );
            }
            measureDocument.head.appendChild(headNodeClone);
        }
        measureDocument.body.appendChild(editableCloneEl.cloneNode(true));
        return styleSheetsSettled;
    }

    /**
     * @param {Element} sourceEl
     * @param {Element} targetEl
     * @returns {void}
     */
    copyAttributes(sourceEl, targetEl) {
        for (const { name, value } of sourceEl.attributes) {
            targetEl.setAttribute(name, value);
        }
    }

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
    }

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
    }
}

registry.category("website-plugins").add(LcpMarkingPlugin.id, LcpMarkingPlugin);
registry.category("translation-plugins").add(LcpMarkingPlugin.id, LcpMarkingPlugin);
