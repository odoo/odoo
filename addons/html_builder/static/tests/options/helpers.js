import { getWebsiteSnippets } from "../snippets_getter.hoot";
import { setupWebsiteBuilder } from "../website_helpers";
import { mockService } from "@web/../tests/web_test_helpers";

export async function getStructureSnippet(snippetName) {
    const html = await getWebsiteSnippets();
    const snippetsDocument = new DOMParser().parseFromString(html, "text/html");
    return snippetsDocument.querySelector(`[data-snippet=${snippetName}]`).cloneNode(true);
}

export async function insertStructureSnippet(editor, snippetName) {
    const snippetEl = await getStructureSnippet(snippetName);
    const parentEl = editor.editable.querySelector("#wrap") || editor.editable;
    parentEl.append(snippetEl);
    editor.shared.history.addStep();
}

export async function setupWebsiteBuilderWithSnippet(snippetName, options = {}) {
    mockService("website", {
        get currentWebsite() {
            return {
                metadata: {
                    defaultLangName: "English (US)",
                },
                id: 1,
            };
        },
    });
    const snippetEl = await getStructureSnippet(snippetName);
    return setupWebsiteBuilder(snippetEl.outerHTML, {
        ...options,
        hasToCreateWebsite: false,
    });
}
