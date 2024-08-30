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
 * Server-side, HTML is stored as a string without HTML entities. This
 * function can be used to convert strings with HTML entities to strings
 * comparable to the format stored server-side (i.e. to determine if a record
 * HTML value has changed compared with its value in the Form view).
 *
 * @param { string } string i.e. innerHTML or outerHTML
 * @returns { string } without HTML entities (i.e. &quot;)
 */
export function decodeHTMLEntities(string) {
    const textarea = document.createElement("textarea");
    textarea.innerHTML = string;
    return textarea.value;
}
