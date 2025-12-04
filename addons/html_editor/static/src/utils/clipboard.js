/**
 * Add origin to relative img src.
 * @param {Document} doc
 * @param {string} origin
 */
function prependOriginToImages(doc, origin) {
    doc.querySelectorAll("img").forEach((img) => {
        const src = img.getAttribute("src");
        if (src && !/^(http|\/\/|data:)/.test(src)) {
            img.src = origin + (src.startsWith("/") ? src : "/" + src);
        }
    });
}

/**
 * Fills clipboard data, also with the
 * application/vnd.odoo.odoo-editor mimetype so that it can recognized
 * on paste inside an editor.
 * @param {ClipboardEvent} ev copy event
 * @param {string} textContent
 * @param {DocumentFragment} clonedContents
 */
export function fillClipboardData(ev, textContent, clonedContents) {
    const doc = ev.target.ownerDocument;
    const dataHtmlElement = doc.createElement("data");
    dataHtmlElement.append(clonedContents);
    prependOriginToImages(dataHtmlElement, doc.defaultView.location.origin);
    const odooHtml = dataHtmlElement.innerHTML;
    const odooText = textContent;
    ev.clipboardData.setData("text/plain", odooText);
    ev.clipboardData.setData("text/html", odooHtml);
    ev.clipboardData.setData("application/vnd.odoo.odoo-editor", odooHtml);
}
