import { advanceTime, press, queryAll, queryAllTexts, queryOne } from "@odoo/hoot-dom";
import { setupEditor } from "./_helpers/editor";
import { setSelection } from "./_helpers/selection";
import { deleteBackward, insertText } from "./_helpers/user_actions";
import { expectElementCount } from "./_helpers/ui_expectations";
import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { nodeSize } from "@html_editor/utils/position";
import { EMBEDDED_COMPONENT_PLUGINS } from "@html_editor/plugin_sets";
import { MAIN_EMBEDDINGS } from "@html_editor/others/embedded_components/embedding_sets";

const configWithEmbeddedTableOfContent = {
    includePlugins: EMBEDDED_COMPONENT_PLUGINS,
    resources: { embedded_components: MAIN_EMBEDDINGS },
};

test("should update table of contents when heading is removed with backspace", async () => {
    const { editor } = await setupEditor("<p>[]first</p><h1>second</h1>", {
        config: configWithEmbeddedTableOfContent,
    });
    await insertText(editor, "/tableofcontent");
    await expectElementCount(".o-we-powerbox", 1);
    expect(queryAllTexts(".o-we-command-name")[0]).toBe("Table of Contents");
    await press("Enter");
    // TOC update is debounced
    await advanceTime(500);
    expect(queryAll(".o_embedded_toc_link")).toHaveCount(1);
    setSelection({ anchorNode: queryOne("h1"), anchorOffset: 0 });
    deleteBackward(editor);
    // TOC update is debounced
    await advanceTime(500);
    expect(queryAll(".o_embedded_toc_link")).toHaveCount(0);
});

test("should update table of contents when heading is converted to paragraph", async () => {
    const { editor } = await setupEditor("<p>[]first</p><h1>second</h1>", {
        config: configWithEmbeddedTableOfContent,
    });
    await insertText(editor, "/tableofcontent");
    await expectElementCount(".o-we-powerbox", 1);
    expect(queryAllTexts(".o-we-command-name")[0]).toBe("Table of Contents");
    await press("Enter");
    // TOC update is debounced
    await advanceTime(500);
    expect(queryAll(".o_embedded_toc_link")).toHaveCount(1);
    const h1 = queryOne("h1");
    setSelection({ anchorNode: h1, anchorOffset: 0, focusNode: h1, focusOffset: nodeSize(h1) });
    await expectElementCount(".o-we-toolbar", 1);
    await contains(".o-we-toolbar [name='font_type'].dropdown-toggle").click();
    await contains(".o_font_type_selector_menu .dropdown-item:contains('Paragraph')").click();

    // TOC update is debounced
    await advanceTime(500);
    expect(queryAll(".o_embedded_toc_link")).toHaveCount(0);
});
