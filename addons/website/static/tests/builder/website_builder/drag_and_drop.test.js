import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    dummyBase64Img,
    getDragMoveHelper,
    setupWebsiteBuilderWithSnippet,
    waitForEndOfOperation,
} from "../website_helpers";

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
    const { getEditableContent } = await setupWebsiteBuilderWithSnippet(
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
