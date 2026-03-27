import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import {
    dummyBase64Img,
    getDragHelper,
    getDragMoveHelper,
    waitForEndOfOperation,
} from "@html_builder/../tests/helpers";

defineWebsiteModels();

test("Drag and drop a section and then undo", async () => {
    await setupWebsiteBuilderWithSnippet(["s_text_image", "s_three_columns"]);
    await contains(":iframe section.s_text_image").click();
    expect(".overlay .o_overlay_options .o_move_handle.o_draggable").toHaveCount(1);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    const { moveTo, drop } = await contains(".o_overlay_options .o_move_handle").drag();
    expect(":iframe .oe_drop_zone").toHaveCount(2);
    expect(":iframe .oe_drop_zone:nth-child(1)").toHaveCount(1);
    expect(":iframe .oe_drop_zone:nth-child(3)").toHaveCount(1);

    await moveTo(":iframe .oe_drop_zone:nth-child(3)");
    expect(":iframe .oe_drop_zone:nth-child(3)").toHaveClass("invisible");
    expect(":iframe section.s_text_image:nth-child(4)").toHaveCount(1);

    await drop(getDragMoveHelper());
    expect(":iframe .oe_drop_zone").toHaveCount(0);
    expect(":iframe section.s_text_image:nth-child(2)").toHaveCount(1);
    await waitForEndOfOperation();
    expect(".o-website-builder_sidebar .fa-undo").toBeEnabled();

    await contains(".o-website-builder_sidebar .fa-undo").click();
    expect(":iframe section.s_text_image:nth-child(1)").toHaveCount(1);
});

test("Drag and drop at the same position should not add a step in the history", async () => {
    await setupWebsiteBuilderWithSnippet(["s_text_image", "s_three_columns"]);
    await contains(":iframe section.s_text_image").click();
    expect(".overlay .o_overlay_options .o_move_handle.o_draggable").toHaveCount(1);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    const { moveTo, drop } = await contains(".o_overlay_options .o_move_handle").drag();
    expect(":iframe .oe_drop_zone").toHaveCount(2);

    await moveTo(":iframe .oe_drop_zone:nth-child(3)");
    expect(":iframe .oe_drop_zone:nth-child(3)").toHaveClass("invisible");
    expect(":iframe section.s_text_image:nth-child(4)").toHaveCount(1);

    await moveTo(":iframe .oe_drop_zone:nth-child(1)");
    expect(":iframe .oe_drop_zone:nth-child(1)").toHaveClass("invisible");
    expect(":iframe section.s_text_image:nth-child(2)").toHaveCount(1);

    await drop(getDragMoveHelper());
    expect(":iframe .oe_drop_zone").toHaveCount(0);
    expect(":iframe section.s_text_image:nth-child(1)").toHaveCount(1);
    await waitForEndOfOperation();
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();
});

test("Drag and drop a column toggles the grid mode", async () => {
    await setupWebsiteBuilderWithSnippet(["s_text_image", "s_three_columns"], {
        loadIframeBundles: true,
    });
    await contains(":iframe section.s_text_image .row > div:nth-child(1)").click();
    expect(".overlay .o_overlay_options .o_move_handle.o_draggable").toHaveCount(1);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();
    expect(":iframe section.s_text_image .row").not.toHaveClass("o_grid_mode");

    const { moveTo, drop } = await contains(".o_overlay_options .o_move_handle").drag();
    expect(":iframe .oe_drop_zone.oe_grid_zone").toHaveCount(1);
    expect(":iframe .oe_drop_zone:not(.oe_grid_zone)").toHaveCount(4);

    await moveTo(":iframe .oe_drop_zone.oe_grid_zone");
    expect(":iframe .oe_drop_zone.oe_grid_zone").toHaveClass("invisible");
    expect(":iframe section.s_text_image .row.o_grid_mode > .o_we_background_grid").toHaveCount(1);
    expect(":iframe section.s_text_image .row > .o_we_drag_helper").toHaveCount(1);

    await drop(getDragMoveHelper());
    expect(":iframe .oe_drop_zone").toHaveCount(0);
    expect(":iframe section.s_text_image .row > .o_we_background_grid").toHaveCount(0);
    expect(":iframe section.s_text_image .row > .o_we_drag_helper").toHaveCount(0);
    expect(":iframe section.s_text_image .row.o_grid_mode > .o_grid_item").toHaveCount(2);
    await waitForEndOfOperation();
    expect(".o-website-builder_sidebar .fa-undo").toBeEnabled();
});

test("Drag and drop an image should drag the closest draggable element but not if it is a section", async () => {
    const { getEditableContent, waitSidebarUpdated } = await setupWebsiteBuilderWithSnippet(
        ["s_text_image", "s_three_columns"],
        { loadIframeBundles: true }
    );
    const editable = getEditableContent();
    const imageEl = editable.querySelector(".s_text_image img");
    imageEl.src = dummyBase64Img;

    await contains(":iframe section.s_text_image").click();
    expect(".overlay .o_overlay_options .o_move_handle").toHaveClass("o_draggable");
    expect(":iframe section.s_text_image").not.toHaveClass("o_draggable");

    await contains(":iframe section.s_text_image img").click();
    await waitSidebarUpdated();
    expect(".overlay .o_overlay_options .o_move_handle").toHaveClass("o_draggable");
    expect(":iframe section.s_text_image .row > div:nth-child(2)").toHaveClass("o_draggable");

    const { drop } = await contains(":iframe section.s_text_image img").drag();
    expect(":iframe .oe_drop_zone.oe_grid_zone").toHaveCount(1);
    expect(":iframe .oe_drop_zone:not(.oe_grid_zone)").toHaveCount(4);
    await drop(getDragMoveHelper());
});

test("A column in mobile view should not be draggable", async () => {
    await setupWebsiteBuilderWithSnippet("s_text_image");
    await contains("button[data-action='mobile']").click();

    await contains(":iframe section.s_text_image").click();
    expect(".overlay .o_overlay_options .o_move_handle").toHaveClass("o_draggable");

    await contains(":iframe section.s_text_image .row > div:nth-child(1)").click();
    expect(".overlay .o_overlay_options .o_move_handle").toHaveCount(0);
});

test("Drag and drop an inner content as a grid item", async () => {
    await setupWebsiteBuilder(
        `<section class="s_dummy" style="width: 600px;">
            <div class="container">
                <div class="row o_grid_mode" data-row-count="3">
                    <div class="o_grid_item g-height-3 g-col-lg-6 col-lg-6" style="grid-area: 1 / 1 / 4 / 7; z-index: 1;">
                        <p>Text</p>
                    </div>
                </div>
            </div>
        </section>
        `,
        { loadIframeBundles: true }
    );
    // Drag over the grid and drop it as an inner content.
    let dragUtils = await contains("#snippet_content [name='Alert'] .o_snippet_thumbnail").drag();
    expect(":iframe .oe_drop_zone").toHaveCount(3);
    expect(":iframe .oe_grid_zone").toHaveCount(1);
    await dragUtils.moveTo(":iframe .oe_grid_zone", { position: { x: 555, y: 55 } });
    expect(":iframe .o_we_background_grid").toHaveCount(1);
    expect(":iframe .o_grid_item").toHaveCount(2);
    await dragUtils.moveTo(":iframe .oe_drop_zone:not(.oe_grid_zone)");
    expect(":iframe .o_we_background_grid").toHaveCount(0);
    expect(":iframe .o_grid_item").toHaveCount(1);
    expect(":iframe .oe_grid_zone").toHaveClass("invisible");
    await dragUtils.drop(getDragHelper());
    await waitForEndOfOperation();
    expect(":iframe .o_grid_item:only-child div.s_alert").toHaveCount(1);
    await contains(".o-website-builder_sidebar .fa-undo").click();
    expect(":iframe div.s_alert").toHaveCount(0);

    // Drag over the grid and drop it as a grid item.
    dragUtils = await contains("#snippet_content [name='Alert'] .o_snippet_thumbnail").drag();
    expect(":iframe .oe_drop_zone").toHaveCount(3);
    expect(":iframe .oe_grid_zone").toHaveCount(1);
    await dragUtils.moveTo(":iframe .oe_grid_zone", { position: { x: 555, y: 55 } });
    expect(":iframe .o_we_background_grid").toHaveCount(1);
    expect(":iframe .o_grid_item").toHaveCount(2);
    expect(":iframe .o_we_drag_helper").toHaveStyle({
        gridRowStart: 2,
        gridColumnStart: 7,
        gridColumnEnd: 13,
    });
    await dragUtils.moveTo(":iframe .oe_grid_zone", { position: { x: 5, y: 205 } });
    await dragUtils.drop(getDragHelper());
    await waitForEndOfOperation();
    expect(":iframe .o_grid_item:nth-child(2)").toHaveStyle({
        zIndex: 2,
        gridRowStart: 5,
        gridColumnStart: 1,
        gridColumnEnd: 7,
    });
    await contains(".o-website-builder_sidebar .fa-undo").click();
    expect(":iframe div.s_alert").toHaveCount(0);

    // Drop near the grid (should become a grid item in the top left corner).
    dragUtils = await contains("#snippet_content [name='Alert'] .o_snippet_thumbnail").drag();
    expect(":iframe .oe_drop_zone").toHaveCount(3);
    expect(":iframe .oe_grid_zone").toHaveCount(1);
    await dragUtils.moveTo({ position: { x: 700, y: 55 } });
    await dragUtils.drop(getDragHelper());
    await waitForEndOfOperation();
    expect(":iframe .o_grid_item").toHaveCount(2);
    expect(":iframe .o_grid_item:nth-child(2)").toHaveStyle({
        zIndex: 2,
        gridRowStart: 1,
        gridColumnStart: 1,
        gridColumnEnd: 7,
    });
});

test("Dragging an inner content from the sidebar in mobile view should not make grid dropzones appear", async () => {
    await setupWebsiteBuilderWithSnippet("s_banner", { loadIframeBundles: true });
    let dragUtils = await contains("#snippet_content [name='Alert'] .o_snippet_thumbnail").drag();
    expect(":iframe .oe_grid_zone").toHaveCount(1);
    await dragUtils.drop(getDragHelper());
    await waitForEndOfOperation();
    expect(":iframe .s_alert").toHaveCount(0);

    // Toggle the mobile preview.
    await contains(".o-snippets-top-actions [data-action='mobile']").click();
    expect(".o_website_preview").toHaveClass("o_is_mobile");
    dragUtils = await contains("#snippet_content [name='Alert'] .o_snippet_thumbnail").drag();
    expect(":iframe .oe_grid_zone").toHaveCount(0);
    await dragUtils.cancel();
});

test("Dragging an inner content from the page should not make grid dropzones appear", async () => {
    await setupWebsiteBuilderWithSnippet("s_banner", { loadIframeBundles: true });
    // Add an inner snippet in the first column.
    let dragUtils = await contains("#snippet_content [name='Alert'] .o_snippet_thumbnail").drag();
    expect(":iframe .oe_grid_zone").toHaveCount(1);
    await dragUtils.moveTo(":iframe .oe_drop_zone");
    await dragUtils.drop(getDragHelper());
    await waitForEndOfOperation();
    expect(":iframe .o_grid_item:nth-child(1) > .s_alert").toHaveCount(1);

    // Redrag the snippet.
    await contains(":iframe .s_alert").click();
    dragUtils = await contains(".o_overlay_options .o_move_handle").drag();
    expect(":iframe .oe_grid_zone").toHaveCount(0);
    await dragUtils.moveTo(":iframe .oe_drop_zone");
    await dragUtils.drop(getDragMoveHelper());
    await waitForEndOfOperation();

    // Check in mobile view.
    await contains(".o-snippets-top-actions [data-action='mobile']").click();
    expect(".o_website_preview").toHaveClass("o_is_mobile");
    const { cancel } = await contains(".o_overlay_options .o_move_handle").drag();
    expect(":iframe .oe_grid_zone").toHaveCount(0);
    await cancel();
});
