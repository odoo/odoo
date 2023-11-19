/** @odoo-module **/

/**
 * @param { Document } document
 * @param { string } html
 * @returns { DocumentFragment }
 */
export function parseHTML(document, html) {
    const fragment = document.createDocumentFragment();
    const parser = new document.defaultView.DOMParser();
    const parsedDocument = parser.parseFromString(html, "text/html");
    fragment.replaceChildren(...parsedDocument.body.childNodes);
    return fragment;
}
