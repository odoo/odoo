import { expect, getFixture, test } from "@odoo/hoot";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { localization } from "@web/core/l10n/localization";
import { queryOne } from "@odoo/hoot-dom";
import {
    getDragHelper,
    getDragMoveHelper,
    setupHTMLBuilder,
    waitForEndOfOperation,
    waitForSnippetDialog,
} from "@html_builder/../tests/helpers";

test("Drag and drop basic test", async () => {
    const dropzoneSelectors = {
        selector: "section",
        dropNear: "section",
    };

    await setupHTMLBuilder(
        `
            <section class="section-1"><div><p>Text 1</p></div></section>
            <section class="section-2"><div><p>Text 2</p></div></section>
        `,
        { dropzoneSelectors }
    );

    await contains(":iframe section.section-1").click();
    expect(".overlay .o_overlay_options .o_move_handle.o_draggable").toHaveCount(1);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    const { moveTo, drop } = await contains(".o_overlay_options .o_move_handle").drag();
    expect(":iframe .oe_drop_zone").toHaveCount(2);
    expect(":iframe .oe_drop_zone:nth-child(1)").toHaveCount(1);
    expect(":iframe .oe_drop_zone:nth-child(3)").toHaveCount(1);

    await moveTo(":iframe .oe_drop_zone:nth-child(3)");
    expect(":iframe .oe_drop_zone:nth-child(3)").toHaveClass("invisible");
    expect(":iframe section.section-1:nth-child(4)").toHaveCount(1);

    await drop(getDragMoveHelper());
    expect(":iframe .oe_drop_zone").toHaveCount(0);
    expect(":iframe section.section-1:nth-child(2)").toHaveCount(1);
    await waitForEndOfOperation();
    expect(".o-website-builder_sidebar .fa-undo").toBeEnabled();
});

test("Can drop a snippet outside a dropzone in a rtl language", async () => {
    // Simulate rtl
    patchWithCleanup(localization, { direction: "rtl" });
    // Visual styling to run the test in debug.
    getFixture().style.setProperty("direction", "rtl");
    const dropzoneSelectors = {
        selector: "section",
        dropIn: "*",
    };
    await setupHTMLBuilder("", { dropzoneSelectors });
    document.body.classList.add("o_rtl");
    const { moveTo, drop } = await contains(
        ".o_snippets_container .o_snippet.o_draggable .o_snippet_thumbnail"
    ).drag();
    expect(":iframe .oe_drop_zone").toHaveCount(1);
    // Move the snippet out of the sidebar, but not over a dropzone
    await moveTo(":iframe body", {
        position: { x: 500, y: 500 },
    });
    expect(":iframe .oe_drop_zone").not.toHaveClass("o_dropzone_highlighted");
    await drop(getDragHelper());
    await waitForSnippetDialog();
    expect(".o_add_snippet_dialog").toHaveCount(1);
});

test("Dragging the last element out of a snippet removes the snippet", async () => {
    // Setup a DOM with two simulated snippets.
    const dropzoneSelectors = {
        selector: ".inner-column",
        dropNear: ".inner-column",
    };

    const { getEditor } = await setupHTMLBuilder(
        `
            <section class="mock-snippet-1">
                <div class="inner-column"><p>Content 1</p></div>
            </section>
            <section class="mock-snippet-2">
                <div class="inner-column"><p>Content 2</p></div>
            </section>
        `,
        { dropzoneSelectors }
    );
    expect(":iframe section").toHaveCount(2);

    const draggedColumnEl = queryOne(":iframe section.mock-snippet-1 .inner-column");
    await contains(":iframe section.mock-snippet-1 .inner-column").click();
    expect(".overlay .o_overlay_options .o_move_handle.o_draggable").toHaveCount(1);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    // Drag the child out of snippet 1 and verify the snippet has been removed.
    const { moveTo, drop } = await contains(".o_overlay_options .o_move_handle").drag();
    await moveTo(":iframe section.mock-snippet-2 .inner-column");
    await drop(getDragMoveHelper());
    await waitForEndOfOperation();
    expect(":iframe section.mock-snippet-1").toHaveCount(0);
    expect(":iframe section").toHaveCount(1);
    expect(":iframe section.mock-snippet-2 .inner-column").toHaveCount(2);

    // Check if the dragged element stays activated even though its old parent
    // snippet was removed during the drop.
    expect(getEditor().shared.builderOptions.getTarget()).toBe(draggedColumnEl);

    // Check undoing
    expect(".o-website-builder_sidebar .fa-undo").toBeEnabled();
    await contains(".o-website-builder_sidebar .fa-undo").click();

    expect(":iframe section").toHaveCount(2);
    expect(":iframe section.mock-snippet-1 .inner-column").toHaveCount(1);
});
