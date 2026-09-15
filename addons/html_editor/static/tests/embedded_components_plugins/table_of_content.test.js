import { delay, describe, expect, test, waitFor } from "@odoo/hoot";
import { setupEditor } from "../_helpers/editor";
import { press, queryOne } from "@odoo/hoot-dom";
import { execCommand } from "../_helpers/userCommands";
import { EMBEDDED_COMPONENT_PLUGINS, MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { TableOfContentPlugin } from "@html_editor/others/embedded_components/plugins/table_of_content_plugin/table_of_content_plugin";
import { MAIN_EMBEDDINGS } from "@html_editor/others/embedded_components/embedding_sets";
import { setSelection } from "../_helpers/selection";
import { expectElementCount } from "../_helpers/ui_expectations";
import { childNodeIndex } from "@html_editor/utils/position";
import { DELAY_TOOLBAR_OPEN } from "@html_editor/main/toolbar/toolbar_plugin";

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

    test("toolbar should not be displayed when selection is around a table of content", async () => {
        const { editor } = await setupEditor("<p>[]<br></p>", {
            config: configWithEmbeddedTableOfContent,
        });
        execCommand(editor, "insertTableOfContent");
        await waitFor(`.o_embedded_toc_content`);
        // Set selection around TOC
        const toc = queryOne(`[data-embedded="tableOfContent"]`);
        setSelection({
            anchorNode: toc.parentNode,
            anchorOffset: childNodeIndex(toc),
            focusNode: toc.parentNode,
            focusOffset: childNodeIndex(toc) + 1,
        });
        await delay(DELAY_TOOLBAR_OPEN);
        await expectElementCount(".o-we-toolbar", 0);
    });
});
