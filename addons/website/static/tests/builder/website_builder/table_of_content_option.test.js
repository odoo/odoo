import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { insertText, undo } from "@html_editor/../tests/_helpers/user_actions";
import { expect, test } from "@odoo/hoot";
import { click, queryAll, queryOne, queryAllTexts, tick, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    insertStructureSnippet,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("edit title in content with table of content", async () => {
    const { getEditor } = await setupWebsiteBuilderWithSnippet("s_table_of_content");
    const editor = getEditor();
    expect(":iframe .s_table_of_content").toHaveCount(1);
    expect(queryAllTexts(":iframe .s_table_of_content_navbar a")).toEqual([
        "Intuitive system",
        "Design features",
    ]);
    expect(queryAllTexts(":iframe .s_table_of_content_main h2")).toEqual([
        "Intuitive system",
        "Design features",
    ]);

    const h2 = queryAll(":iframe .s_table_of_content_main h2:contains('Intuitive system')")[0];
    setSelection({ anchorNode: h2, anchorOffset: 0 });
    await insertText(editor, "New Title:");
    expect(queryAllTexts(":iframe .s_table_of_content_navbar a")).toEqual([
        "New Title:Intuitive system",
        "Design features",
    ]);
    expect(queryAllTexts(":iframe .s_table_of_content_main h2")).toEqual([
        "New Title:Intuitive system",
        "Design features",
    ]);

    undo(editor);
    expect(queryAllTexts(":iframe .s_table_of_content_navbar a")).toEqual([
        "New TitleIntuitive system",
        "Design features",
    ]);
    expect(queryAllTexts(":iframe .s_table_of_content_main h2")).toEqual([
        "New TitleIntuitive system",
        "Design features",
    ]);
});

test("click on addItem option button", async () => {
    const { getEditor } = await setupWebsiteBuilderWithSnippet("s_table_of_content");
    const editor = getEditor();
    expect(queryAllTexts(":iframe .s_table_of_content_navbar a")).toEqual([
        "Intuitive system",
        "Design features",
    ]);
    expect(queryAllTexts(":iframe .s_table_of_content_main h2")).toEqual([
        "Intuitive system",
        "Design features",
    ]);

    await contains(":iframe .s_table_of_content_main h2").click();
    await contains("[data-action-id='addItem']").click();
    expect(queryAllTexts(":iframe .s_table_of_content_vertical_navbar a")).toEqual([
        "Intuitive system",
        "Design features",
        "Design features",
    ]);
    expect(queryAllTexts(":iframe .s_table_of_content_main h2")).toEqual([
        "Intuitive system",
        "Design features",
        "Design features",
    ]);

    undo(editor);
    expect(queryAllTexts(":iframe .s_table_of_content_vertical_navbar a")).toEqual([
        "Intuitive system",
        "Design features",
    ]);
    expect(queryAllTexts(":iframe .s_table_of_content_main h2")).toEqual([
        "Intuitive system",
        "Design features",
    ]);
});

test("hide title in content with table of content", async () => {
    const { getEditor } = await setupWebsiteBuilderWithSnippet("s_table_of_content");
    const editor = getEditor();
    expect(":iframe .s_table_of_content").toHaveCount(1);
    expect(queryAllTexts(":iframe .s_table_of_content_navbar a")).toEqual([
        "Intuitive system",
        "Design features",
    ]);

    // Hide title
    await contains(":iframe .s_table_of_content_main h2").click();
    await waitFor(".options-container");
    const sectionOptionContainer = queryAll(".options-container").pop();
    expect(sectionOptionContainer.querySelector("div")).toHaveText("Section");
    await click(sectionOptionContainer.querySelector("[data-action-id='toggleDeviceVisibility']"));
    await tick();
    expect(queryAllTexts(":iframe .s_table_of_content_navbar a")).toEqual(["Design features"]);

    undo(editor);
    expect(queryAllTexts(":iframe .s_table_of_content_navbar a")).toEqual([
        "Intuitive system",
        "Design features",
    ]);
});

test("remove main content with table of content", async () => {
    const { getEditor } = await setupWebsiteBuilderWithSnippet("s_table_of_content");
    const editor = getEditor();
    expect(":iframe .s_table_of_content").toHaveCount(1);
    expect(queryAllTexts(":iframe .s_table_of_content_navbar a")).toEqual([
        "Intuitive system",
        "Design features",
    ]);

    await contains(":iframe .s_table_of_content_main h2").click();
    await contains(".overlay .oe_snippet_remove").click();
    expect(queryAllTexts(":iframe .s_table_of_content_navbar a")).toEqual(["Design features"]);

    await contains(":iframe .s_table_of_content_main h2").click();
    await contains(".overlay .oe_snippet_remove").click();
    expect(":iframe .s_table_of_content").toHaveCount(0);
    expect(":iframe .s_table_of_content_navbar a").toHaveCount(0);

    undo(editor);
    expect(queryAllTexts(":iframe .s_table_of_content_navbar a")).toEqual(["Design features"]);
});
test("update second toc navbar", async () => {
    const { getEditor } = await setupWebsiteBuilderWithSnippet("s_table_of_content");
    const editor = getEditor();
    await insertStructureSnippet(editor, "s_table_of_content");
    const toc1Anchor1El = queryOne(
        ":iframe .s_table_of_content:nth-child(1) .s_table_of_content_navbar a:nth-child(1)"
    );
    const toc1Anchor2El = queryOne(
        ":iframe .s_table_of_content:nth-child(1) .s_table_of_content_navbar a:nth-child(2)"
    );
    const toc2Anchor1El = queryOne(
        ":iframe .s_table_of_content:nth-child(2) .s_table_of_content_navbar a:nth-child(1)"
    );
    const toc2Anchor2El = queryOne(
        ":iframe .s_table_of_content:nth-child(2) .s_table_of_content_navbar a:nth-child(2)"
    );
    expect(toc1Anchor1El.getAttribute("href")).not.toEqual(toc2Anchor1El.getAttribute("href"));
    expect(toc1Anchor2El.getAttribute("href")).not.toEqual(toc2Anchor2El.getAttribute("href"));
});
