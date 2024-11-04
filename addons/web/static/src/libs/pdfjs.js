import { isMobileOS } from "@web/core/browser/feature_detection";
import { loadJS } from "@web/core/assets";

/**
 * Until we have our own implementation of the /web/static/lib/pdfjs/web/viewer.{html,js,css}
 * (currently based on Firefox), this method allows us to hide the buttons that we do not want:
 * * All edit buttons
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
    const hiddenElements = [
        "#editorModeButtons",
        "button#openFile",
        "button#secondaryOpenFile",
        "a#viewBookmark",
        "a#secondaryViewBookmark",
    ];
    if (isMobileOS()) {
        hiddenElements.push([
            "button#downloadButton",
            "button#secondaryDownload",
            "button#printButton",
            "button#secondaryPrint",
        ]);
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
        loadJS("/web/static/lib/pdfjs/build/pdf.js"),
        loadJS("/web/static/lib/pdfjs/build/pdf.worker.js"),
    ]);
}
