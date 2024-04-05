/** @odoo-module **/

import { isMobileOS } from "@web/core/browser/feature_detection";
import { loadJS } from "@web/core/assets";

/**
 * Until we have our own implementation of the /web/static/lib/pdfjs/web/viewer.{html,js,css}
 * (currently based on Firefox), this method allows us to hide the buttons that we do not want:
 * * "Open File"
 * * "View Bookmark"
 * * "Print" (Hidden on mobile device like Android, iOS, ...)
 * * "Download" (Hidden on mobile device like Android, iOS, ...)
 *
 * @link https://mozilla.github.io/pdf.js/getting_started/
 *
 * @param {Element} rootElement
 */
export function hidePDFJSButtons(rootElement) {
    const cssStyle = document.createElement("style");
    cssStyle.rel = "stylesheet";
    cssStyle.textContent = `button#secondaryOpenFile.secondaryToolbarButton, button#openFile.toolbarButton,
    button#editorFreeText.toolbarButton, button#editorInk.toolbarButton, button#editorStamp.toolbarButton,
    button#secondaryOpenFile.secondaryToolbarButton,
a#secondaryViewBookmark.secondaryToolbarButton, a#viewBookmark.toolbarButton {
display: none !important;
}`;
    if (isMobileOS()) {
        cssStyle.textContent = `${cssStyle.innerHTML}
button#secondaryDownload.secondaryToolbarButton, button#download.toolbarButton,
button#editorFreeText.toolbarButton, button#editorInk.toolbarButton, button#editorStamp.toolbarButton,
button#secondaryPrint.secondaryToolbarButton, button#print.toolbarButton{
display: none !important;
}`;
    }
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
        loadJS("/web/static/lib/pdfjs/build/pdf.js"),
        loadJS("/web/static/lib/pdfjs/build/pdf.worker.js"),
    ]);
}
