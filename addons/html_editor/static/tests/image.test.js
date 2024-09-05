import { expect, test } from "@odoo/hoot";
import { click, queryOne, waitFor, waitUntil } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { setupEditor } from "./_helpers/editor";
import { contains } from "@web/../tests/web_test_helpers";
import { setContent } from "./_helpers/selection";
import { undo } from "./_helpers/user_actions";

const base64Img =
    "data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAAUA\n        AAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO\n            9TXL0Y4OHwAAAABJRU5ErkJggg==";

test("image can be selected", async () => {
    const { editor } = await setupEditor(`
        <img src="${base64Img}">
    `);

    await click("img");
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='image_shape']").toHaveCount(1);
    const selectionPlugin = editor.plugins.find((p) => p.constructor.name === "selection");
    expect(selectionPlugin.getSelectedNodes()[0].tagName).toBe("IMG");
});

test("can shape an image", async () => {
    await setupEditor(`
        <img src="${base64Img}">
    `);
    const img = queryOne("img");
    await click(img);
    await waitFor(".o-we-toolbar");

    const buttons = {};
    for (const buttonName of ["shape_rounded", "shape_circle", "shape_shadow", "shape_thumbnail"]) {
        buttons[buttonName] = `.o-we-toolbar button[name='${buttonName}']`;
    }

    await click(buttons["shape_rounded"]);
    await animationFrame();
    expect(buttons["shape_rounded"]).toHaveClass("active");
    expect(img).toHaveClass("rounded");

    await click(buttons["shape_rounded"]);
    await animationFrame();
    expect(buttons["shape_rounded"]).not.toHaveClass("active");
    expect(img).not.toHaveClass("rounded");

    await click(buttons["shape_circle"]);
    await animationFrame();
    expect(buttons["shape_circle"]).toHaveClass("active");
    expect(img).toHaveClass("rounded-circle");

    await click(buttons["shape_shadow"]);
    await animationFrame();
    expect(buttons["shape_shadow"]).toHaveClass("active");
    expect(img).toHaveClass("shadow");

    await click(buttons["shape_thumbnail"]);
    await animationFrame();
    expect(buttons["shape_thumbnail"]).toHaveClass("active");
    expect(img).toHaveClass("img-thumbnail");
});

test("shape_circle and shape_rounded are mutually exclusive", async () => {
    await setupEditor(`
        <img src="${base64Img}">
    `);
    const img = queryOne("img");
    await click(img);
    await waitFor(".o-we-toolbar");

    const buttons = {};
    for (const buttonName of ["shape_rounded", "shape_circle", "shape_shadow", "shape_thumbnail"]) {
        buttons[buttonName] = `.o-we-toolbar button[name='${buttonName}']`;
    }

    await click(buttons["shape_rounded"]);
    await animationFrame();
    expect(buttons["shape_rounded"]).toHaveClass("active");
    expect(img).toHaveClass("rounded");

    await click(buttons["shape_circle"]);
    await animationFrame();
    expect(buttons["shape_circle"]).toHaveClass("active");
    expect(img).toHaveClass("rounded-circle");
    expect(buttons["shape_rounded"]).not.toHaveClass("active");
    expect(img).not.toHaveClass("rounded");

    await click(buttons["shape_rounded"]);
    await animationFrame();
    expect(buttons["shape_rounded"]).toHaveClass("active");
    expect(img).toHaveClass("rounded");
    expect(buttons["shape_circle"]).not.toHaveClass("active");
    expect(img).not.toHaveClass("rounded-circle");
});

test("can undo a shape", async () => {
    const { editor } = await setupEditor(`
        <img src="${base64Img}">
    `);
    await click("img");
    await waitFor(".o-we-toolbar");

    await click(".o-we-toolbar button[name='shape_rounded']");
    await animationFrame();
    expect(".o-we-toolbar button[name='shape_rounded']").toHaveClass("active");
    expect("img").toHaveClass("rounded");
    undo(editor);
    await animationFrame();
    expect(".o-we-toolbar button[name='shape_rounded']").not.toHaveClass("active");
    expect("img").not.toHaveClass("rounded");
});

test("can add an image description & tooltip", async () => {
    await setupEditor(`
        <img src="${base64Img}">
    `);
    await click("img");
    await waitFor(".o-we-toolbar");

    await click(".o-we-toolbar .btn-group[name='image_description'] button");
    await animationFrame();

    expect(".modal-body").toHaveCount(1);
    await contains("input[name='description']").edit("description modified");
    await contains("input[name='tooltip']").edit("tooltip modified");
    await click(".modal-footer button");
    await animationFrame();
    expect("img").toHaveAttribute("alt", "description modified");
    expect("img").toHaveAttribute("title", "tooltip modified");
});

test("can edit an image description & tooltip", async () => {
    await setupEditor(`
        <img class="img-fluid test-image" src="${base64Img}" alt="description" title="tooltip">
    `);
    await click("img.test-image");
    await waitFor(".o-we-toolbar");

    await click(".o-we-toolbar .btn-group[name='image_description'] button");
    await animationFrame();

    expect(".modal-body").toHaveCount(1);
    expect("input[name='description']").toHaveValue("description");
    expect("input[name='tooltip']").toHaveValue("tooltip");
    await contains("input[name='description']").edit("description modified");
    await contains("input[name='tooltip']").edit("tooltip modified");
    await click(".modal-footer button");
    await animationFrame();
    expect("img").toHaveAttribute("alt", "description modified");
    expect("img").toHaveAttribute("title", "tooltip modified");
});

test("Can change an image size", async () => {
    await setupEditor(`
        <img class="img-fluid test-image" src="${base64Img}">
    `);
    await click("img.test-image");
    await waitFor(".o-we-toolbar");
    expect(queryOne("img").style.width).toBe("");
    expect(".o-we-toolbar button[name='resize_default']").toHaveClass("active");

    await click(".o-we-toolbar button[name='resize_100']");
    await animationFrame();
    expect(queryOne("img").style.width).toBe("100%");
    expect(".o-we-toolbar button[name='resize_100']").toHaveClass("active");

    await click(".o-we-toolbar button[name='resize_50']");
    await animationFrame();
    expect(queryOne("img").style.width).toBe("50%");
    expect(".o-we-toolbar button[name='resize_50']").toHaveClass("active");

    await click(".o-we-toolbar button[name='resize_25']");
    await animationFrame();
    expect(queryOne("img").style.width).toBe("25%");
    expect(".o-we-toolbar button[name='resize_25']").toHaveClass("active");

    await click(".o-we-toolbar button[name='resize_default']");
    await animationFrame();
    expect(queryOne("img").style.width).toBe("");
    expect(".o-we-toolbar button[name='resize_default']").toHaveClass("active");
});

test("Can undo the image sizing", async () => {
    const { editor } = await setupEditor(`
        <img class="img-fluid test-image" src="${base64Img}">
    `);
    await click("img.test-image");
    await waitFor(".o-we-toolbar");

    await click(".o-we-toolbar button[name='resize_100']");
    await animationFrame();
    expect(queryOne("img").style.width).toBe("100%");
    expect(".o-we-toolbar button[name='resize_100']").toHaveClass("active");

    undo(editor);
    expect(queryOne("img").style.width).toBe("");
});

test("Can change the padding of an image", async () => {
    await setupEditor(`
        <img class="img-fluid test-image" src="${base64Img}">
    `);
    await click("img.test-image");
    await waitFor(".o-we-toolbar");

    await click(".o-we-toolbar div[name='image_padding'] button");
    await animationFrame();
    await click(".o_popover div:contains('Small')");
    await animationFrame();
    expect("img").toHaveClass("p-1");

    await click(".o-we-toolbar div[name='image_padding'] button");
    await animationFrame();
    await click(".o_popover div:contains('Medium')");
    await animationFrame();
    expect("img").not.toHaveClass("p-1");
    expect("img").toHaveClass("p-2");

    await click(".o-we-toolbar div[name='image_padding'] button");
    await animationFrame();
    await click(".o_popover div:contains('Large')");
    await animationFrame();
    expect("img").not.toHaveClass("p-2");
    expect("img").toHaveClass("p-3");

    await click(".o-we-toolbar div[name='image_padding'] button");
    await animationFrame();
    await click(".o_popover div:contains('XL')");
    await animationFrame();
    expect("img").not.toHaveClass("p-3");
    expect("img").toHaveClass("p-5");

    await click(".o-we-toolbar div[name='image_padding'] button");
    await animationFrame();
    await click(".o_popover div:contains('None')");
    await animationFrame();
    expect("img").not.toHaveClass("p-5");
});

test("Can undo the image padding", async () => {
    const { editor } = await setupEditor(`
        <img class="img-fluid test-image" src="${base64Img}" alt="description" title="tooltip">
    `);
    await click("img.test-image");
    await waitFor(".o-we-toolbar");

    await click(".o-we-toolbar div[name='image_padding'] button");
    await animationFrame();
    await click(".o_popover div:contains('Small')");
    await animationFrame();
    expect("img").toHaveClass("p-1");

    undo(editor);
    await animationFrame();
    expect("img").not.toHaveClass("p-1");
});

test("Can preview an image", async () => {
    await setupEditor(`
        <img class="img-fluid test-image" src="${base64Img}">
    `);
    await click("img.test-image");
    await waitFor(".o-we-toolbar");
    await click(".o-we-toolbar button[name='image_preview']");
    await animationFrame();
    expect(".o-FileViewer").toHaveCount(1);
});

test("Can transform an image", async () => {
    await setupEditor(`
        <img class="img-fluid test-image" src="${base64Img}">
    `);
    await click("img.test-image");
    await waitFor(".o-we-toolbar");
    await click(".o-we-toolbar button[name='image_transform']");
    await animationFrame();
    const transfoContainers = document.querySelectorAll(".transfo-container");
    expect(transfoContainers).toHaveCount(1);
    // The created transformation container is outside of the hoot fixture, clean it manually
    for (const transfoContainer of transfoContainers) {
        transfoContainer.remove();
    }
});

test("Image transformation dissapear when selection change", async () => {
    const { el } = await setupEditor(`
        <img class="img-fluid test-image" src="${base64Img}">
        <p> Hello world </p>
    `);
    await click("img.test-image");
    await waitFor(".o-we-toolbar");
    await click(".o-we-toolbar button[name='image_transform']");
    await animationFrame();
    let transfoContainers = document.querySelectorAll(".transfo-container");
    expect(transfoContainers).toHaveCount(1);

    setContent(
        el,
        `<img class="img-fluid test-image" src="/web/static/img/logo.png">
        <p> [Hello] world </p> `
    );
    await waitUntil(() => !document.querySelector(".transfo-container"));
    transfoContainers = document.querySelectorAll(".transfo-container");
    expect(transfoContainers).toHaveCount(0);
    // Remove the transfoContainer element if not destroyed by the selection change
    for (const transfoContainer of transfoContainers) {
        transfoContainer.remove();
    }
});

test("Can delete an image", async () => {
    await setupEditor(`
        <p> <img class="img-fluid test-image" src="${base64Img}"> </p>
    `);
    expect(".test-image").toHaveCount(1);
    await click("img");
    await waitFor(".o-we-toolbar");
    expect("button[name='image_delete']").toHaveCount(1);
    await click("button[name='image_delete']");
    await animationFrame();
    expect(".test-image").toHaveCount(0);
});

test("Toolbar detect image namespace even if it is the only child of a p", async () => {
    await setupEditor(`
        <p><img class="img-fluid test-image" src="${base64Img}"></p>
    `);
    expect(".test-image").toHaveCount(1);
    await click("img");
    await waitFor(".o-we-toolbar");
    expect("button[name='image_delete']").toHaveCount(1);
});

test("Toolbar detects image namespace when there is text next to it", async () => {
    await setupEditor(`
        <p><img class="img-fluid test-image" src="${base64Img}">abc</p>
    `);
    expect(".test-image").toHaveCount(1);
    await click("img");
    await waitFor(".o-we-toolbar");
    expect("button[name='image_delete']").toHaveCount(1);
});

test("Toolbar should not be namespaced for image", async () => {
    await setupEditor(`
        <p>a[bc<img class="img-fluid test-image" src="${base64Img}">]def</p>
    `);
    await waitFor(".o-we-toolbar");
    expect("button[name='image_delete']").toHaveCount(0);
});

test("can add link on an image", async () => {
    await setupEditor(`
        <img src="${base64Img}">
    `);
    const img = queryOne("img");
    await click("img");
    await waitFor(".o-we-toolbar");
    await click("button[name='link']");
    await animationFrame();

    await contains(".o-we-linkpopover input.o_we_href_input_link").fill("http://odoo.com/");
    await animationFrame();
    expect(img.parentElement.tagName).toBe("A");
    expect(img.parentElement).toHaveAttribute("href", "http://odoo.com/");
});

test("can undo adding link to image", async () => {
    const { editor } = await setupEditor(`
        <img src="${base64Img}">
    `);
    const img = queryOne("img");
    await click("img");
    await waitFor(".o-we-toolbar");
    await click("button[name='link']");
    await animationFrame();
    await contains(".o-we-linkpopover input.o_we_href_input_link").fill("http://odoo.com/");
    await animationFrame();
    expect(img.parentElement.tagName).toBe("A");

    undo(editor);
    await animationFrame();
    expect(img.parentElement.tagName).toBe("P");
});

test("can remove the link of an image", async () => {
    await setupEditor(`
        <a href="#"><img src="${base64Img}"></a>
    `);
    const img = queryOne("img");
    await click("img");
    await waitFor(".o-we-toolbar");
    expect("button[name='unlink']").toHaveCount(1);
    await click("button[name='unlink']");
    await animationFrame();
    expect(img.parentElement.tagName).toBe("P");
    expect(".o-we-linkpopover").toHaveCount(0);
});

test("can undo link removing of an image", async () => {
    const { editor } = await setupEditor(`
        <a href="#"><img src="${base64Img}"></a>
    `);
    const img = queryOne("img");
    await click("img");
    await waitFor(".o-we-toolbar");
    await click("button[name='unlink']");
    await animationFrame();
    expect(img.parentElement.tagName).toBe("P");

    undo(editor);
    await animationFrame();
    expect(img.parentElement.tagName).toBe("A");
});
