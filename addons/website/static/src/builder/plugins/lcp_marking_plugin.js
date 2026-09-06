import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { delay } from "@web/core/utils/concurrency";
import { getBgImageURLFromEl } from "@html_builder/utils/utils_css";
import { SIZES, MEDIAS_BREAKPOINTS } from "@web/core/ui/ui_utils";

const DESKTOP_LCP_VIEWPORT_SIZE = {
    width: MEDIAS_BREAKPOINTS[SIZES["LG"]]["maxWidth"],
    height: 768,
};

const MOBILE_LCP_VIEWPORT_SIZE = {
    width: MEDIAS_BREAKPOINTS[SIZES["MD"]]["maxWidth"],
    height: 667,
};

const DEVICE_HIDDEN_SELECTOR =
    ".o_snippet_mobile_invisible[data-invisible], .o_snippet_desktop_invisible[data-invisible]";
const PRIORITY_IMAGE_SELECTOR = "img[fetchpriority='high']";
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

    async startLcpMeasurement() {
        const record = this.lcpRecord();
        if (!this.editable || !record || !this.services.website.isDesigner) {
            return;
        }
        return this.saveLcpImages(record, this.snapshotEditable());
    }

    snapshotEditable() {
        const editableCloneEl = this.editable.cloneNode(true);
        editableCloneEl.removeAttribute("contenteditable");
        for (const hiddenEl of editableCloneEl.querySelectorAll(DEVICE_HIDDEN_SELECTOR)) {
            hiddenEl.removeAttribute("data-invisible");
            hiddenEl.classList.remove("o_snippet_override_invisible");
        }
        for (const imgEl of editableCloneEl.querySelectorAll("img")) {
            imgEl.setAttribute("loading", "eager");
        }
        return { editableCloneEl, sourceDocument: this.editable.ownerDocument };
    }

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
            context: { website_id: this.services.website.currentWebsite.id },
        });
    }

    lcpRecord() {
        const metadata = this.services.website?.currentWebsite?.metadata;
        return metadata?.seoObject || metadata?.mainObject || null;
    }

    preserveImageFieldSrc(elements, { node }) {
        if (!node?.parentElement?.matches("[data-oe-type='image']")) {
            return;
        }
        const source = node.getAttribute(IMAGE_FIELD_SRC_ATTRIBUTE) || node.getAttribute("src");
        if (!source) {
            return;
        }
        for (const imageEl of elements) {
            if (imageEl?.tagName === "IMG") {
                imageEl.setAttribute(IMAGE_FIELD_SRC_ATTRIBUTE, source);
            }
        }
    }

    cleanForSave(rootEl) {
        for (const imgEl of rootEl.querySelectorAll(`[${IMAGE_FIELD_SRC_ATTRIBUTE}]`)) {
            imgEl.removeAttribute(IMAGE_FIELD_SRC_ATTRIBUTE);
        }
        for (const imgEl of rootEl.querySelectorAll(PRIORITY_IMAGE_SELECTOR)) {
            imgEl.removeAttribute("loading");
            imgEl.removeAttribute("fetchpriority");
        }
        return rootEl;
    }

    async electImageUrl(viewport, snapshot) {
        const { hostEl, iframeEl } = await this.appendMeasureFrame(viewport);
        try {
            const measureDocument = iframeEl.contentDocument;
            if (!measureDocument) {
                return undefined;
            }
            this.fillMeasurementDocument(measureDocument, snapshot);
            await this.waitForMeasurementResources(measureDocument);
            const entryEl = await this.observeLcpEntry(measureDocument.defaultView);
            return entryEl === undefined ? undefined : this.imageUrl(entryEl);
        } finally {
            hostEl.remove();
        }
    }

    imageUrl(el) {
        const source =
            el.tagName === "IMG"
                ? el.getAttribute(IMAGE_FIELD_SRC_ATTRIBUTE) || el.getAttribute("src")
                : getBgImageURLFromEl(el);
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

    measurementScale(viewport) {
        return Math.min(
            1,
            window.innerWidth / viewport.width,
            window.innerHeight / viewport.height
        );
    }

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

    copyAttributes(sourceEl, targetEl) {
        for (const { name, value } of sourceEl.attributes) {
            targetEl.setAttribute(name, value);
        }
    }

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

    async observeLcpEntry(win) {
        const IframePerformanceObserver = win.PerformanceObserver;
        const supported = IframePerformanceObserver?.supportedEntryTypes?.includes(
            "largest-contentful-paint"
        );
        if (!supported) {
            return undefined;
        }
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
        return entries.at(-1)?.element ?? undefined;
    }
}

registry.category("website-plugins").add(LcpMarkingPlugin.id, LcpMarkingPlugin);
