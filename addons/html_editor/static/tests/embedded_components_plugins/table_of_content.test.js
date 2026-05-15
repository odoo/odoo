import { describe, expect, test, waitFor } from "@odoo/hoot";
import { setupEditor } from "../_helpers/editor";
import { press } from "@odoo/hoot-dom";
import { execCommand } from "../_helpers/userCommands";
import { EMBEDDED_COMPONENT_PLUGINS, MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { TableOfContentPlugin } from "@html_editor/others/embedded_components/plugins/table_of_content_plugin/table_of_content_plugin";
import { MAIN_EMBEDDINGS } from "@html_editor/others/embedded_components/embedding_sets";

const configWithEmbeddedTableOfContent = {
    Plugins: [
        ...MAIN_PLUGINS.filter((P) => P.id !== "tableOfContent"),
        TableOfContentPlugin,
        ...EMBEDDED_COMPONENT_PLUGINS,
    ],
    resources: { embedded_components: MAIN_EMBEDDINGS },
};

describe("Table of content", () => {
    test("Should properly undo table of content (1)", async () => {
        const { editor } = await setupEditor("<p>[]<br></p>", {
            config: configWithEmbeddedTableOfContent,
        });
        execCommand(editor, "insertTableOfContent");
        await waitFor(`.o-we-hint`);
        await waitFor(`.o_embedded_toc_content`);
        expect(".o_embedded_toc_content").toHaveCount(1);
        await press(["Ctrl", "z"]);
        expect(".o_embedded_toc_content").toHaveCount(0);
    });
    test("Should properly undo table of content (2)", async () => {
        const { editor } = await setupEditor("<p>a[]b</p>", {
            config: configWithEmbeddedTableOfContent,
        });
        execCommand(editor, "insertTableOfContent");
        await waitFor(`.o_embedded_toc_content`);
        expect(".o_embedded_toc_content").toHaveCount(1);
        await press(["Ctrl", "z"]);
        expect(".o_embedded_toc_content").toHaveCount(0);
    });
});
