import { startInteractions } from "@web/../tests/public/helpers";
import { getStructureSnippet } from "../snippet_helpers";

/**
 * @param {string | string[]} snippetName
 * @param {{
 *   withImgSrc?: boolean,
 *   processHTML?: (containerEl: HTMLElement) => void,
 *   startOptions?: object,
 * }} options
 */
export async function startInteractionsWithSnippet(snippetName, options = {}) {
    const { withImgSrc, processHTML, startOptions } = options;
    const containerEl = document.createElement("t");
    const snippetNames = Array.isArray(snippetName) ? snippetName : [snippetName];
    for (const name of snippetNames) {
        const el = await getStructureSnippet(name, withImgSrc);
        containerEl.appendChild(el);
    }
    if (processHTML) {
        processHTML(containerEl);
    }
    return startInteractions(containerEl.innerHTML, startOptions);
}
