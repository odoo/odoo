import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { deleteBackward, insertText, undo } from "@html_editor/../tests/_helpers/user_actions";
import { expect, test } from "@odoo/hoot";
import {
    animationFrame,
    click,
    manuallyDispatchProgrammaticEvent,
    press,
    queryAll,
    queryAllTexts,
    queryFirst,
    queryOne,
    tick,
    waitFor,
} from "@odoo/hoot-dom";
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
    expect(
        queryAllTexts(":iframe .s_table_of_content_navbar a.table_of_content_link_depth_0")
    ).toEqual(["Intuitive system", "Design features"]);
    expect(queryAllTexts(":iframe .s_table_of_content_main h2")).toEqual([
        "Intuitive system",
        "Design features",
    ]);

    const h2 = queryAll(":iframe .s_table_of_content_main h2:contains('Intuitive system')")[0];
    setSelection({ anchorNode: h2, anchorOffset: 0 });
    await insertText(editor, "New Title:");
    expect(
        queryAllTexts(":iframe .s_table_of_content_navbar a.table_of_content_link_depth_0")
    ).toEqual(["New Title:Intuitive system", "Design features"]);
    expect(queryAllTexts(":iframe .s_table_of_content_main h2")).toEqual([
        "New Title:Intuitive system",
        "Design features",
    ]);

    undo(editor);
    expect(
        queryAllTexts(":iframe .s_table_of_content_navbar a.table_of_content_link_depth_0")
    ).toEqual(["New TitleIntuitive system", "Design features"]);
    expect(queryAllTexts(":iframe .s_table_of_content_main h2")).toEqual([
        "New TitleIntuitive system",
        "Design features",
    ]);
});

test("click on addItem option button", async () => {
    const { getEditor } = await setupWebsiteBuilderWithSnippet("s_table_of_content");
    const editor = getEditor();
    expect(
        queryAllTexts(":iframe .s_table_of_content_navbar a.table_of_content_link_depth_0")
    ).toEqual(["Intuitive system", "Design features"]);
    expect(queryAllTexts(":iframe .s_table_of_content_main h2")).toEqual([
        "Intuitive system",
        "Design features",
    ]);

    await contains(":iframe .s_table_of_content_main h2").click();
    await contains("[data-action-id='addItem']").click();
    expect(
        queryAllTexts(":iframe .s_table_of_content_vertical_navbar a.table_of_content_link_depth_0")
    ).toEqual(["Intuitive system", "Design features", "Design features"]);
    expect(queryAllTexts(":iframe .s_table_of_content_main h2")).toEqual([
        "Intuitive system",
        "Design features",
        "Design features",
    ]);

    undo(editor);
    expect(
        queryAllTexts(":iframe .s_table_of_content_vertical_navbar a.table_of_content_link_depth_0")
    ).toEqual(["Intuitive system", "Design features"]);
    expect(queryAllTexts(":iframe .s_table_of_content_main h2")).toEqual([
        "Intuitive system",
        "Design features",
    ]);
});

test("hide title in content with table of content", async () => {
    const { getEditor } = await setupWebsiteBuilderWithSnippet("s_table_of_content");
    const editor = getEditor();
    expect(":iframe .s_table_of_content").toHaveCount(1);
    expect(
        queryAllTexts(":iframe .s_table_of_content_navbar a.table_of_content_link_depth_0")
    ).toEqual(["Intuitive system", "Design features"]);

    // Hide title
    await contains(":iframe .s_table_of_content_main h2").click();
    await waitFor(".options-container");
    const sectionOptionContainer = queryAll(".options-container").pop();
    expect(sectionOptionContainer.querySelector("div")).toHaveText("Section");
    await click(sectionOptionContainer.querySelector("[data-action-id='toggleDeviceVisibility']"));
    await tick();
    expect(
        queryAllTexts(":iframe .s_table_of_content_navbar a.table_of_content_link_depth_0")
    ).toEqual(["Design features"]);

    undo(editor);
    expect(
        queryAllTexts(":iframe .s_table_of_content_navbar a.table_of_content_link_depth_0")
    ).toEqual(["Intuitive system", "Design features"]);
});

test("properly sets the level of depth for a new heading", async () => {
    const { getEditor } = await setupWebsiteBuilderWithSnippet("s_table_of_content");
    const editor = getEditor();
    expect(":iframe .s_table_of_content_navbar a").toHaveCount(6);

    // we create a new heading h4 after h3
    setSelection({
        anchorNode: queryOne(":iframe #table_of_content_heading_1_4 + p"),
        anchorOffset: 1,
    });
    await press("enter");
    await manuallyDispatchProgrammaticEvent(editor.editable, "beforeinput", {
        inputType: "insertParagraph",
    });
    await insertText(editor, "New Subheading");

    const newSubheadingEl = queryOne(":iframe .s_table_of_content p:contains('New Subheading')");
    setSelection({
        anchorNode: newSubheadingEl.firstChild,
        anchorOffset: 0,
        focusOffset: newSubheadingEl.firstChild.length,
    });
    await waitFor(".o-we-toolbar");
    await click(".o-we-toolbar .btn[name=font]");
    await animationFrame();
    await click(".o-dropdown-item[name='h4']");
    expect(":iframe .s_table_of_content_navbar a").toHaveCount(7);
    // it should have depth 2:
    // h2
    // |-h3
    // |--h4 New Subheading
    expect(":iframe .s_table_of_content_navbar a.table_of_content_link_depth_2").toHaveCount(1);
    expect(":iframe .s_table_of_content_navbar a.table_of_content_link_depth_2").toHaveText(
        "New Subheading"
    );
});

test("updates depth after removing a heading", async () => {
    const { getEditor } = await setupWebsiteBuilderWithSnippet("s_table_of_content");
    const editor = getEditor();
    expect(":iframe .s_table_of_content_navbar a").toHaveCount(6);
    expect(":iframe .s_table_of_content_navbar a.table_of_content_link_depth_0").toHaveCount(2);
    expect(":iframe .s_table_of_content_navbar a.table_of_content_link_depth_1").toHaveCount(4);
    // current structure:
    // h2
    // |-h3
    // |-h3
    // h2
    // |-h3
    // |-h3
    const firstHeadingEl = queryFirst(":iframe .s_table_of_content h2");
    // remove text from the heading
    setSelection({
        anchorNode: firstHeadingEl,
        focusNode: firstHeadingEl,
        focusOffset: 1,
    });
    deleteBackward(editor);

    // remove the heading itself
    setSelection({
        anchorNode: firstHeadingEl,
    });
    deleteBackward(editor);

    // updated structure:
    // h3
    // h3
    // h2
    // |-h3
    // |-h3
    expect(":iframe .s_table_of_content_navbar a").toHaveCount(5);
    expect(":iframe .s_table_of_content_navbar a.table_of_content_link_depth_0").toHaveCount(3);
    expect(":iframe .s_table_of_content_navbar a.table_of_content_link_depth_1").toHaveCount(2);
});

test("remove main content with table of content", async () => {
    const { getEditor } = await setupWebsiteBuilderWithSnippet("s_table_of_content");
    const editor = getEditor();
    expect(":iframe .s_table_of_content").toHaveCount(1);
    expect(queryAllTexts(":iframe .s_table_of_content_navbar a")).toEqual([
        "Intuitive system",
        "What you see is what you get",
        "Customization tool",
        "Design features",
        "Building blocks system",
        "Bootstrap-Based Templates",
    ]);

    await contains(":iframe .s_table_of_content_main h2").click();
    await contains(".overlay .oe_snippet_remove").click();
    expect(queryAllTexts(":iframe .s_table_of_content_navbar a")).toEqual([
        "Design features",
        "Building blocks system",
        "Bootstrap-Based Templates",
    ]);

    await contains(":iframe .s_table_of_content_main h2").click();
    await contains(".overlay .oe_snippet_remove").click();
    expect(":iframe .s_table_of_content").toHaveCount(0);
    expect(":iframe .s_table_of_content_navbar a").toHaveCount(0);

    undo(editor);
    expect(queryAllTexts(":iframe .s_table_of_content_navbar a")).toEqual([
        "Design features",
        "Building blocks system",
        "Bootstrap-Based Templates",
    ]);
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
