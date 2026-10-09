import { getBgImageURLFromEl } from "@html_builder/utils/utils_css";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { MEDIAS_BREAKPOINTS, SIZES } from "@web/core/ui/ui_utils";
import { delay } from "@web/core/utils/concurrency";

/**
 * @typedef {{ width: number, height: number }} LcpViewport
 * @typedef {{ editableCloneEl: HTMLElement, sourceDocument: Document }} LcpSnapshot
 * @typedef {{ model: string, id: number }} LcpRecord
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
        return this.saveLcpImages(record, this.snapshotEditable());
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
     * @param {LcpViewport} viewport
     * @param {LcpSnapshot} snapshot
     * @returns {Promise<string | false | undefined>}
     */
    async electImageUrl(viewport, snapshot) {
        const { hostEl, iframeEl } = await this.appendMeasureFrame(viewport);
        try {
            const measureDocument = iframeEl.contentDocument;
            this.fillMeasurementDocument(measureDocument, snapshot);
            await this.waitForMeasurementResources(measureDocument);
            const entryEl = await this.observeLcpEntry(measureDocument.defaultView);
            return entryEl === undefined ? undefined : this.imageUrl(entryEl);
        } finally {
            hostEl.remove();
        }
    }

    /**
     * @param {Element} el
     * @returns {string | false}
     */
    imageUrl(el) {
        let source;
        switch (el.tagName) {
            case "IMG":
                source = el.getAttribute(IMAGE_FIELD_SRC_ATTRIBUTE) || el.getAttribute("src");
                break;
            default:
                source = getBgImageURLFromEl(el);
        }
        if (!source) {
            return false;
        }
        const { origin } = window.location;
        const url = new URL(source, origin);
        if (!["http:", "https:"].includes(url.protocol)) {
            return false;
        }
        return url.origin === origin ? url.pathname + url.search : url.href;
    }

    /**
     * @param {LcpViewport} viewport
     * @returns {Promise<{ hostEl: HTMLDivElement, iframeEl: HTMLIFrameElement }>}
     */
    async appendMeasureFrame(viewport) {
        const hostEl = document.createElement("div");
        hostEl.setAttribute("aria-hidden", "true");
        const scale = this.measurementScale(viewport);
        hostEl.style.cssText =
            "position: fixed; top: 0; left: 0; pointer-events: none; filter: opacity(0);" +
            `transform: scale(${scale}); transform-origin: 0 0;`;
        const iframeEl = document.createElement("iframe");
        iframeEl.style.cssText = `border: 0; width: ${viewport.width}px; height: ${viewport.height}px;`;
        hostEl.attachShadow({ mode: "closed" }).appendChild(iframeEl);
        await new Promise((resolve) => {
            iframeEl.addEventListener("load", resolve, { once: true });
            document.body.appendChild(hostEl);
        });
        return { hostEl, iframeEl };
    }

    /**
     * @param {LcpViewport} viewport
     * @returns {number}
     */
    measurementScale(viewport) {
        return Math.min(
            1,
            window.innerWidth / viewport.width,
            window.innerHeight / viewport.height
        );
    }

    /**
     * @param {Document} measureDocument
     * @param {LcpSnapshot} snapshot
     * @returns {void}
     */
    fillMeasurementDocument(measureDocument, { editableCloneEl, sourceDocument }) {
        this.copyAttributes(sourceDocument.documentElement, measureDocument.documentElement);
        measureDocument.documentElement.classList.remove("o_is_mobile");
        this.copyAttributes(sourceDocument.body, measureDocument.body);
        for (const headNode of sourceDocument.head.childNodes) {
            if (headNode.tagName === "SCRIPT") {
                continue;
            }
            measureDocument.head.appendChild(headNode.cloneNode(true));
        }
        measureDocument.body.appendChild(editableCloneEl.cloneNode(true));
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
     * @returns {Promise<void>}
     */
    async waitForMeasurementResources(measureDocument) {
        const styleSheetEls = [...measureDocument.querySelectorAll("link[rel='stylesheet']")];
        await Promise.all([
            ...styleSheetEls.map(
                (linkEl) =>
                    linkEl.sheet ||
                    new Promise((resolve) => {
                        linkEl.addEventListener("load", resolve, { once: true });
                        linkEl.addEventListener("error", resolve, { once: true });
                    })
            ),
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
