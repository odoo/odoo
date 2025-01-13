import { SnippetModel } from "@html_builder/builder/snippet_model";
import { getMockEnv } from "@web/../tests/web_test_helpers";

export async function insertStructureSnippet(editor, snippetName) {
    const snippetModel = new SnippetModel(getMockEnv().services, {
        snippetsName: "website.snippets",
        installSnippetModule: () => {},
    });
    await snippetModel.load();
    const snippet = snippetModel.snippetsByCategory.snippet_structure.find(
        (snippet) => snippet.name === snippetName
    );
    editor.editable.append(snippet.content.cloneNode(true));
    editor.shared.history.addStep();
}
