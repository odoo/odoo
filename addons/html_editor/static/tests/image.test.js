import { expect, test } from "@odoo/hoot";
import { click, queryOne, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { setupEditor } from "./_helpers/editor";
import { contains } from "@web/../tests/web_test_helpers";

test("image can be selected", async () => {
    const { editor } = await setupEditor(`
        <img class="img-fluid" src="/web/static/img/logo.png">
    `);
    click("img");
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='image_shape']").toHaveCount(1);
    const selectionPlugin = editor.plugins.find((p) => p.constructor.name === "selection");
    expect(selectionPlugin.getSelectedNodes()[0].tagName).toBe("IMG");
});

test("can shape an image", async () => {
    await setupEditor(`
        <img class="img-fluid" src="/web/static/img/logo.png">
    `);
    click("img");
    await waitFor(".o-we-toolbar");

    click(".o-we-toolbar .fa-square");
    await animationFrame();
    expect(".o-we-toolbar .fa-square.active").toHaveCount(1);
    expect("img.rounded").toHaveCount(1);

    click(".o-we-toolbar .fa-square");
    await animationFrame();
    expect(".o-we-toolbar .fa-square.active").toHaveCount(0);
    expect("img.rounded").toHaveCount(0);

    click(".o-we-toolbar .fa-circle-o");
    await animationFrame();
    expect(".o-we-toolbar .fa-circle-o.active").toHaveCount(1);
    expect("img.rounded-circle").toHaveCount(1);

    click(".o-we-toolbar .fa-sun-o");
    await animationFrame();
    expect(".o-we-toolbar .fa-sun-o.active").toHaveCount(1);
    expect("img.shadow").toHaveCount(1);

    click(".o-we-toolbar .fa-picture-o");
    await animationFrame();
    expect(".o-we-toolbar .fa-picture-o.active").toHaveCount(1);
    expect("img.img-thumbnail").toHaveCount(1);
});

test("can undo a shape", async () => {
    const { editor } = await setupEditor(`
        <img class="img-fluid" src="/web/static/img/logo.png">
    `);
    click("img");
    await waitFor(".o-we-toolbar");

    click(".o-we-toolbar .fa-square");
    await animationFrame();
    expect(".o-we-toolbar .fa-square.active").toHaveCount(1);
    expect("img.rounded").toHaveCount(1);
    editor.dispatch("HISTORY_UNDO");
    await animationFrame();
    expect(".o-we-toolbar .fa-square.active").toHaveCount(0);
    expect("img.rounded").toHaveCount(0);
});

test("can add an image description & tooltip", async () => {
    await setupEditor(`
        <img class="img-fluid" src="/web/static/img/logo.png">
    `);
    click("img");
    await waitFor(".o-we-toolbar");

    click(".o-we-toolbar .btn-group[name='image_description'] button");
    await animationFrame();

    expect(".modal-body").toHaveCount(1);
    await contains("input[name='description']").edit("description modified");
    await contains("input[name='tooltip']").edit("tooltip modified");
    click(".modal-footer button");
    await animationFrame();
    expect("img").toHaveAttribute("alt", "description modified");
    expect("img").toHaveAttribute("title", "tooltip modified");
});

test("can edit an image description & tooltip", async () => {
    await setupEditor(`
        <img class="img-fluid test-image" src="/web/static/img/logo.png" alt="description" title="tooltip">
    `);
    click("img.test-image");
    await waitFor(".o-we-toolbar");

    click(".o-we-toolbar .btn-group[name='image_description'] button");
    await animationFrame();

    expect(".modal-body").toHaveCount(1);
    expect("input[name='description']").toHaveValue("description");
    expect("input[name='tooltip']").toHaveValue("tooltip");
    await contains("input[name='description']").edit("description modified");
    await contains("input[name='tooltip']").edit("tooltip modified");
    click(".modal-footer button");
    await animationFrame();
    expect("img").toHaveAttribute("alt", "description modified");
    expect("img").toHaveAttribute("title", "tooltip modified");
});

test("Can change an image size", async () => {
    await setupEditor(`
        <img class="img-fluid test-image" src="/web/static/img/logo.png">
    `);
    click("img.test-image");
    await waitFor(".o-we-toolbar");
    expect(queryOne("img").style.width).toBe("");
    expect(".o-we-toolbar button[name='resize_default']").toHaveClass("active");

    click(".o-we-toolbar button[name='resize_100']");
    await animationFrame();
    expect(queryOne("img").style.width).toBe("100%");
    expect(".o-we-toolbar button[name='resize_100']").toHaveClass("active");

    click(".o-we-toolbar button[name='resize_50']");
    await animationFrame();
    expect(queryOne("img").style.width).toBe("50%");
    expect(".o-we-toolbar button[name='resize_50']").toHaveClass("active");

    click(".o-we-toolbar button[name='resize_25']");
    await animationFrame();
    expect(queryOne("img").style.width).toBe("25%");
    expect(".o-we-toolbar button[name='resize_25']").toHaveClass("active");

    click(".o-we-toolbar button[name='resize_default']");
    await animationFrame();
    expect(queryOne("img").style.width).toBe("");
    expect(".o-we-toolbar button[name='resize_default']").toHaveClass("active");
});

test("Can undo the image sizing", async () => {
    const { editor } = await setupEditor(`
        <img class="img-fluid test-image" src="/web/static/img/logo.png">
    `);
    click("img.test-image");
    await waitFor(".o-we-toolbar");

    click(".o-we-toolbar button[name='resize_100']");
    await animationFrame();
    expect(queryOne("img").style.width).toBe("100%");
    expect(".o-we-toolbar button[name='resize_100']").toHaveClass("active");

    editor.dispatch("HISTORY_UNDO");
    expect(queryOne("img").style.width).toBe("");
});

test("Can change the padding of an image", async () => {
    await setupEditor(`
        <img class="img-fluid test-image" src="/web/static/img/logo.png">
    `);
    click("img.test-image");
    await waitFor(".o-we-toolbar");

    click(".o-we-toolbar div[name='image_padding'] button");
    await animationFrame();
    click(".o_popover div:contains('Small')");
    await animationFrame();
    expect("img").toHaveClass("p-1");

    click(".o-we-toolbar div[name='image_padding'] button");
    await animationFrame();
    click(".o_popover div:contains('Medium')");
    await animationFrame();
    expect("img").not.toHaveClass("p-1");
    expect("img").toHaveClass("p-2");

    click(".o-we-toolbar div[name='image_padding'] button");
    await animationFrame();
    click(".o_popover div:contains('Large')");
    await animationFrame();
    expect("img").not.toHaveClass("p-2");
    expect("img").toHaveClass("p-3");

    click(".o-we-toolbar div[name='image_padding'] button");
    await animationFrame();
    click(".o_popover div:contains('XL')");
    await animationFrame();
    expect("img").not.toHaveClass("p-3");
    expect("img").toHaveClass("p-5");

    click(".o-we-toolbar div[name='image_padding'] button");
    await animationFrame();
    click(".o_popover div:contains('None')");
    await animationFrame();
    expect("img").not.toHaveClass("p-5");
});

test("Can undo the image padding", async () => {
    const { editor } = await setupEditor(`
        <img class="img-fluid test-image" src="/web/static/img/logo.png">
    `);
    click("img.test-image");
    await waitFor(".o-we-toolbar");

    click(".o-we-toolbar div[name='image_padding'] button");
    await animationFrame();
    click(".o_popover div:contains('Small')");
    await animationFrame();
    expect("img").toHaveClass("p-1");

    editor.dispatch("HISTORY_UNDO");
    await animationFrame();
    expect("img").not.toHaveClass("p-1");
});

test("Can preview an image", async () => {
    await setupEditor(`
        <img class="img-fluid test-image" src="/web/static/img/logo.png">
    `);
    click("img.test-image");
    await waitFor(".o-we-toolbar");
    click(".o-we-toolbar button[name='image_preview']");
    await animationFrame();
    expect(".o-FileViewer").toHaveCount(1);
});
