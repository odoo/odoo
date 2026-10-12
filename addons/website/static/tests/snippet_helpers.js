import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { getWebsiteSnippets } from "./snippets_getter.hoot";

const domParserCache = new Map();
export function patchDOMParser() {
    if (DOMParser.prototype.isPatched) {
        return;
    }
    patch(DOMParser.prototype, {
        parseFromString(html, type) {
            if (type !== "text/html") {
                return super.parseFromString(html, type);
            }
            if (domParserCache.has(html)) {
                return domParserCache.get(html).cloneNode(true);
            }
            const res = super.parseFromString(html, type);
            if (res.body?.firstChild?.id === "snippet_groups") {
                // Only cache the document containing the snippets
                domParserCache.set(html, res);
                return res.cloneNode(true);
            }
            return res;
        },
        isPatched: true,
    });
}

export async function getStructureSnippet(snippetName, withImgSrc = false) {
    patchDOMParser();
    const html = await getWebsiteSnippets(withImgSrc);
    const snippetsDocument = new DOMParser().parseFromString(html, "text/html");
    const processors = registry.category("html_builder.snippetsPreprocessor").getAll();
    for (const processor of Object.values(processors)) {
        processor("website.snippets", snippetsDocument);
    }
    const snippetEl = snippetsDocument.querySelector(
        `[data-snippet=${snippetName}]:not([data-snippet] [data-snippet])`
    );
    const el = snippetEl.cloneNode(true);
    el.dataset.name = snippetEl.parentElement.getAttribute("name");
    return el;
}
