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
 * Fills clipboard or dataTransfer data, including the
 * application/vnd.odoo.odoo-editor MIME type so it can be recognized
 * when pasted or dropped inside an editor.
 *
 * @param {ClipboardEvent | DragEvent} ev - The event on which to set the data.
 * @param {'clipboardData' | 'dataTransfer'} transferObjectProperty
 * @param {DocumentFragment} clonedContents
 * @param {Object} [options]
 * @param {boolean} [options.setEditorTransferData=true]
 * @param {string} [options.textContent]
 */

export function fillHtmlTransferData(
    ev,
    transferObjectProperty,
    clonedContents,
    { setEditorTransferData = true, textContent } = {}
) {
    const doc = ev.target.ownerDocument;
    const dataHtmlElement = doc.createElement("data");
    dataHtmlElement.append(clonedContents);
    prependOriginToImages(dataHtmlElement, doc.defaultView.location.origin);
    const htmlContent = dataHtmlElement.innerHTML;
    if (textContent) {
        ev[transferObjectProperty].setData("text/plain", textContent);
    }
    ev[transferObjectProperty].setData("text/html", htmlContent);
    if (setEditorTransferData) {
        ev[transferObjectProperty].setData("application/vnd.odoo.odoo-editor", htmlContent);
    }
}
