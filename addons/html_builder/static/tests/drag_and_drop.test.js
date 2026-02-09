import { expect, getFixture, test } from "@odoo/hoot";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { localization } from "@web/core/l10n/localization";
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
