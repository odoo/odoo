import { isMobileOS } from "@web/core/browser/feature_detection";
import { loadJS } from "@web/core/assets";

/**
 * Until we have our own implementation of the /web/static/lib/pdfjs/web/viewer.{html,js,css}
 * (currently based on Firefox), this method allows us to hide the buttons that we do not want:
 * * All edit buttons
 * * "Open File"
 * * "Current Page" ("#viewBookmark")
 * * "Download" (Hidden on mobile device like Android, iOS, ... or via option)
 * * "Print" (Hidden on mobile device like Android, iOS, ... or via option)
 * * "Presentation" (via options)
 * * "Rotation" (via options)
 *
 * @link https://mozilla.github.io/pdf.js/getting_started/
 *
 * @param {Element} rootElement IFRAME DOM element of PDF.js viewer
 * @param {Object} options options to hide additional buttons
 * @param {boolean} options.hideDownload hide download button
 * @param {boolean} options.hidePrint hide print button
 * @param {boolean} options.hidePresentation hide presentation button
 * @param {boolean} options.hideRotation hide rotation button
 */
export function hidePDFJSButtons(rootElement, options = {}) {
    const hiddenElements = [
        "#editorModeButtons",
        "button#openFile",
        "button#secondaryOpenFile",
        "a#viewBookmark",
        "a#secondaryViewBookmark",
    ];
    if (options.hideDownload || isMobileOS()) {
        hiddenElements.push(["button#downloadButton", "button#secondaryDownload"]);
    }
    if (options.hidePrint || isMobileOS()) {
        hiddenElements.push(["button#printButton", "button#secondaryPrint"]);
    }
    if (options.hidePresentation) {
        hiddenElements.push("button#presentationMode");
    }
    if (options.hideRotation) {
        hiddenElements.push("button#pageRotateCw");
        hiddenElements.push("button#pageRotateCcw");
    }
    const cssStyle = document.createElement("style");
    cssStyle.rel = "stylesheet";
    cssStyle.textContent = `${hiddenElements.join(", ")} {
    display: none !important;
}`;
    const iframe =
        rootElement.tagName === "IFRAME" ? rootElement : rootElement.querySelector("iframe");
    if (iframe) {
        if (!iframe.dataset.hideButtons) {
            iframe.dataset.hideButtons = "true";
            iframe.addEventListener("load", (event) => {
                if (iframe.contentDocument && iframe.contentDocument.head) {
                    iframe.contentDocument.head.appendChild(cssStyle);
                }
            });
        }
    } else {
        console.warn("No IFRAME found");
    }
}

export async function loadPDFJSAssets() {
    return Promise.all([
        loadJS("/web/static/lib/pdfjs/build/pdf.js", { type: "module" }),
        loadJS("/web/static/lib/pdfjs/build/pdf.worker.js", { type: "module" }),
    ]);
}

export async function generatePdfThumbnail(pdfUrl, options = { height: 256, width: 256 }) {
    let initialWorkerSrc = false,
        isPdfValid,
        pdf,
        thumbnail;
    try {
        await loadPDFJSAssets();
        // Force usage of worker to avoid hanging the tab.
        initialWorkerSrc = globalThis.pdfjsLib.GlobalWorkerOptions.workerSrc;
        globalThis.pdfjsLib.GlobalWorkerOptions.workerSrc =
            "/web/static/lib/pdfjs/build/pdf.worker.js";
    } catch {
        return { thumbnail, pdfEnabled: false };
    }
    try {
        // Support for blob url
        if (pdfUrl.startsWith("blob:") && !pdfUrl.startsWith("blob:http")) {
            pdfUrl = URL.createObjectURL(pdfUrl);
            pdf = await globalThis.pdfjsLib.getDocument(pdfUrl).promise;
            URL.revokeObjectURL(pdfUrl);
        } else {
            pdf = await globalThis.pdfjsLib.getDocument(pdfUrl).promise;
        }
    } catch (_error) {
        if (_error.status === 415) {
            isPdfValid = false;
        } else if (
            _error.name !== "UnexpectedResponseException" &&
            _error.status &&
            _error.status !== 403
        ) {
            pdf = undefined;
        }
    } finally {
        // Restore pdfjs's state
        globalThis.pdfjsLib.GlobalWorkerOptions.workerSrc = initialWorkerSrc;
    }
    if (pdf) {
        isPdfValid = true;
        const page = await pdf.getPage(1);
        // Render first page onto a canvas
        const viewPort = page.getViewport({ scale: 1 });
        const canvas = document.createElement("canvas");
        canvas.width = options.width;
        canvas.height = options.height;
        const scale = canvas.width / viewPort.width;
        await page.render({
            canvasContext: canvas.getContext("2d"),
            viewport: page.getViewport({ scale }),
        }).promise;
        thumbnail = canvas.toDataURL("image/jpeg").replace("data:image/jpeg;base64,", "");
    }
    return { isPdfValid, thumbnail, pdfEnabled: true };
}
