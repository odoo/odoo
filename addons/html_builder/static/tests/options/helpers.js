import { getEditable, setupWebsiteBuilder } from "../helpers";
import { SnippetModel } from "@html_builder/builder/snippet_model";
import { getMockEnv, makeMockEnv, mockService } from "@web/../tests/web_test_helpers";

export async function getStructureSnippet(snippetName) {
    const mockEnv = getMockEnv() || (await makeMockEnv());
    const snippetModel = new SnippetModel(mockEnv.services, {
        snippetsName: "website.snippets",
        installSnippetModule: () => {},
    });
    await snippetModel.load();
    const snippet = snippetModel.snippetsByCategory.snippet_structure.find(
        (snippet) => snippet.name === snippetName
    );
    return snippet.content.cloneNode(true);
}

export async function insertStructureSnippet(editor, snippetName) {
    const snippetEl = await getStructureSnippet(snippetName);
    const parentEl = editor.editable.querySelector("#wrap") || editor.editable;
    parentEl.append(snippetEl);
    editor.shared.history.addStep();
}

export async function setupWebsiteBuilderWithSnippet(snippetName) {
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
    return setupWebsiteBuilder(getEditable(snippetEl.outerHTML), {
        hasToCreateWebsite: false,
    });
}
