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

/**
 * Server-side, HTML is stored as a string which can have a different format
 * than what the current browser returns through outerHTML or innerHTML, notably
 * because of HTML entities.
 * This function can be used to convert strings with potential HTML entities to
 * the format used by the current browser. This allows comparisons between
 * values returned by the server and values extracted from the DOM using i.e.
 * innerHTML.
 *
 * @param { string } content
 * @param { function } cleanup receives the body element containing the parsed
 *        html, to perform some cleanup for the comparison.
 * @returns { string }
 */
export function normalizeHTML(content, cleanup = () => {}) {
    const parser = new document.defaultView.DOMParser();
    const body = parser.parseFromString(content, "text/html").body;
    cleanup(body);
    return body.innerHTML;
}
