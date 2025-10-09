/* global Prism */
import { fillEmpty } from "@html_editor/utils/dom";
import { descendants, lastLeaf } from "@html_editor/utils/dom_traversal";

export const DEFAULT_LANGUAGE_ID = "plaintext";

/**
 * Replace newlines in the given `element` with the appropriate number of line
 * breaks to preserve the visual aspect of these line breaks.
 *
 * @param {Element} element
 * @param {Document} [doc = element.ownerDocument || document]
 */
export const newlinesToLineBreaks = (element, doc = element.ownerDocument || document) => {
    // 1. Replace \n with <br>.
    for (const node of descendants(element).filter((node) => node.nodeType === Node.TEXT_NODE)) {
        let newline = node.textContent.indexOf("\n");
        while (newline !== -1) {
            node.before(doc.createTextNode(node.textContent.slice(0, newline)));
            node.before(doc.createElement("BR"));
            node.textContent = node.textContent.slice(newline + 1);
            newline = node.textContent.indexOf("\n");
        }
        if (!node.textContent) {
            node.remove(); // Prevent empty trailing text node that would become the last leaf.
        }
    }
    // 2. Handle trailing BRs. Eg, <span>ab\n</span> -> <span>ab</span><br><br>
    const trailingBr = lastLeaf(element);
    if (trailingBr?.nodeName === "BR") {
        element.append(trailingBr); // <span>ab<br></span> -> <span>ab</span><br>
        trailingBr.after(doc.createElement("BR")); // <br></pre> -> <br><br></pre>
    }
    // 3. Fill empty.
    fillEmpty(element);
};

/**
 * Return the given `<pre>` element's inner text, cleaned of any zero-width
 * characters or trailing invisible newline characters (a trailing `<br>` in
 * the element's HTML is invisible but results in an visible `\n` in its
 * `innerText` property, which would be visible if kept).
 *
 * @param {HTMLPreElement} pre
 * @returns {string}
 */
export const getPreValue = (pre) => {
    // Trailing br gives \n in innerText but should not be visible.
    const trailingBrs = pre.innerHTML.match(/(<br>)+$/)?.length || 0;
    return pre.innerText
        .slice(0, pre.innerText.length - (trailingBrs > 1 ? trailingBrs - 1 : trailingBrs))
        .replace(/[\u200B\uFEFF]/g, "");
};

/**
 * Use the Prism library to highlight the given HTML `value` with the given
 * `languageId` and replace the given `pre`'s inner HTML with it.
 *
 * @param {HTMLPreElement} pre
 * @param {string} value
 * @param {string} languageId
 */
export const highlightPre = (pre, value, languageId) => {
    // We need a temporary element because directly changing the HTML of the
    // PRE, or using replaceChildren both mess up the history by not
    // recording the removal of the contents.
    const fakeElement = pre.ownerDocument.createElement("pre");
    if (window.Prism) {
        fakeElement.innerHTML = Prism.highlight(value, Prism.languages[languageId], languageId);
    } else {
        fakeElement.innerHTML = value;
    }

    // Post-process highlighted HTML.
    newlinesToLineBreaks(fakeElement, pre.ownerDocument);

    // Replace the PRE's contents with the highlighted ones.
    [...pre.childNodes].forEach((child) => child.remove());
    [...fakeElement.childNodes].forEach((child) => pre.append(child));
};
