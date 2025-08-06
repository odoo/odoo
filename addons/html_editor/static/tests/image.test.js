import { expect, test } from "@odoo/hoot";
import {
    click,
    dblclick,
    pointerUp,
    press,
    queryOne,
    waitFor,
    waitForNone,
    manuallyDispatchProgrammaticEvent,
} from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { contains } from "@web/../tests/web_test_helpers";
import { base64Img, setupEditor } from "./_helpers/editor";
import { getContent, moveSelectionOutsideEditor, setContent } from "./_helpers/selection";
import { insertText, undo } from "./_helpers/user_actions";
import { expectElementCount } from "./_helpers/ui_expectations";

test("image can be selected", async () => {
    const { plugins } = await setupEditor(`
        <img src="${base64Img}">
    `);

    await click("img");
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='image_shape']").toHaveCount(1);
    const selectionPlugin = plugins.get("selection");
    expect(selectionPlugin.getTargetedNodes()[0].tagName).toBe("IMG");
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
    await waitFor(buttons["shape_rounded"] + ".active");
    expect(buttons["shape_rounded"]).toHaveClass("active");
    expect(img).toHaveClass("rounded");

    await click(buttons["shape_rounded"]);
    await waitFor(buttons["shape_rounded"] + ":not(.active)");
    expect(buttons["shape_rounded"]).not.toHaveClass("active");
    expect(img).not.toHaveClass("rounded");

    await click(buttons["shape_circle"]);
    await waitFor(buttons["shape_circle"] + ".active");
    expect(buttons["shape_circle"]).toHaveClass("active");
    expect(img).toHaveClass("rounded-circle");

    await click(buttons["shape_shadow"]);
    await waitFor(buttons["shape_shadow"] + ".active");
    expect(buttons["shape_shadow"]).toHaveClass("active");
    expect(img).toHaveClass("shadow");

    await click(buttons["shape_thumbnail"]);
    await waitFor(buttons["shape_thumbnail"] + ".active");
    expect(buttons["shape_thumbnail"]).toHaveClass("active");
    expect(img).toHaveClass("img-thumbnail");
});

test("shape_circle and shape_rounded are mutually exclusive", async () => {
    await setupEditor(`
        <p><img src="${base64Img}"></p>
    `);
    const img = queryOne("img");
    await click(img);
    await waitFor(".o-we-toolbar");

    const buttons = {};
    for (const buttonName of ["shape_rounded", "shape_circle", "shape_shadow", "shape_thumbnail"]) {
        buttons[buttonName] = `.o-we-toolbar button[name='${buttonName}']`;
    }

    await click(buttons["shape_rounded"]);
    await waitFor(buttons["shape_rounded"] + ".active");
    expect(img).toHaveClass("rounded");

    await click(buttons["shape_circle"]);
    await waitFor(buttons["shape_circle"] + ".active");
    expect(img).toHaveClass("rounded-circle");
    expect(buttons["shape_rounded"]).not.toHaveClass("active");
    expect(img).not.toHaveClass("rounded");

    await click(buttons["shape_rounded"]);
    await waitFor(buttons["shape_rounded"] + ".active");
    expect(img).toHaveClass("rounded");
    expect(buttons["shape_circle"]).not.toHaveClass("active");
    expect(img).not.toHaveClass("rounded-circle");
});

test.tags("mobile");
test("can undo a shape", async () => {
    const { editor } = await setupEditor(`
        <img src="${base64Img}">
    `);
    await click("img");
    await waitFor(".o-we-toolbar");

    await click(".o-we-toolbar button[name='shape_rounded']");
    await expectElementCount(".o-we-toolbar button[name='shape_rounded'].active", 1);
    expect("img").toHaveClass("rounded");
    undo(editor);
    await expectElementCount(".o-we-toolbar button[name='shape_rounded'].active", 0);
    expect("img").not.toHaveClass("rounded");
});

test("focus description input by default when image description popover opens", async () => {
    await setupEditor(`
        <img src="${base64Img}">
    `);
    await click("img");
    await waitFor(".o-we-toolbar");

    await click(".o-we-toolbar .btn-group[name='image_description'] button");
    await animationFrame();

    expect(".o-we-image-description-popover").toHaveCount(1);
    expect("input[name='description']").toBeFocused();
});

test("can add an image description & tooltip", async () => {
    await setupEditor(`
        <img src="${base64Img}">
    `);
    await click("img");
    await waitFor(".o-we-toolbar");

    await click(".o-we-toolbar .btn-group[name='image_description'] button");
    await animationFrame();

    expect(".o-we-image-description-popover").toHaveCount(1);
    await contains("input[name='description']").edit("description modified");
    await contains("input[name='tooltip']").edit("tooltip modified");
    await click(".o-we-image-description-popover button");
    await animationFrame();
    expect("img").toHaveAttribute("alt", "description modified");
    expect("img").toHaveAttribute("title", "tooltip modified");
});

test("should close image description popover on escape", async () => {
    await setupEditor(`
        <img src="${base64Img}" alt="description" title="tooltip">
    `);
    await click("img");
    await waitFor(".o-we-toolbar");

    await click(".o-we-toolbar .btn-group[name='image_description'] button");
    await animationFrame();

    expect(".o-we-image-description-popover").toHaveCount(1);
    await contains("input[name='description']").edit("description modified");
    await contains("input[name='tooltip']").edit("tooltip modified");
    await press("Escape");
    await animationFrame();
    expect(".o-we-image-description-popover").toHaveCount(0);
    expect("img").toHaveAttribute("alt", "description");
    expect("img").toHaveAttribute("title", "tooltip");
});

test("can edit an image description & tooltip", async () => {
    await setupEditor(`
        <img class="img-fluid test-image" src="${base64Img}" alt="description" title="tooltip">
    `);
    await click("img.test-image");
    await waitFor(".o-we-toolbar");

    await click(".o-we-toolbar .btn-group[name='image_description'] button");
    await animationFrame();

    expect(".o-we-image-description-popover").toHaveCount(1);
    expect("input[name='description']").toHaveValue("description");
    expect("input[name='tooltip']").toHaveValue("tooltip");
    await contains("input[name='description']").edit("description modified");
    await contains("input[name='tooltip']").edit("tooltip modified");
    await click(".o-we-image-description-popover button");
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

    await click(".o-we-toolbar [name='image_size'] .dropdown-toggle");
    await animationFrame();
    await click(".image_size_selector .dropdown-item:contains('100%')");
    expect(queryOne("img").style.width).toBe("100%");

    await click(".o-we-toolbar [name='image_size'] .dropdown-toggle");
    await animationFrame();
    await click(".image_size_selector .dropdown-item:contains('50%')");
    expect(queryOne("img").style.width).toBe("50%");

    await click(".o-we-toolbar [name='image_size'] .dropdown-toggle");
    await animationFrame();
    await click(".image_size_selector .dropdown-item:contains('25%')");
    expect(queryOne("img").style.width).toBe("25%");

    await click(".o-we-toolbar [name='image_size'] .dropdown-toggle");
    await animationFrame();
    await click(".image_size_selector .dropdown-item:contains('Default')");
    expect(queryOne("img").style.width).toBe("");
});

test("Can undo the image sizing", async () => {
    const { editor } = await setupEditor(`
        <img class="img-fluid test-image" src="${base64Img}">
    `);
    await click("img.test-image");
    await waitFor(".o-we-toolbar");

    await click(".o-we-toolbar [name='image_size'] .dropdown-toggle");
    await animationFrame();
    await click(".image_size_selector .dropdown-item:contains('100%')");
    expect(queryOne("img").style.width).toBe("100%");

    undo(editor);
    expect(queryOne("img").style.width).toBe("");
});

test("Can change the padding of an image", async () => {
    await setupEditor(`
        <img class="img-fluid test-image" src="${base64Img}">
    `);
    await click("img.test-image");
    await waitFor(".o-we-toolbar");

    await click(".o-we-toolbar div[name='image_padding'] .dropdown-toggle");
    await animationFrame();
    await click(".o-dropdown--menu span:contains('Small')");
    await animationFrame();
    expect("img").toHaveClass("p-1");

    await click(".o-we-toolbar div[name='image_padding'] .dropdown-toggle");
    await animationFrame();
    await click(".o-dropdown--menu span:contains('Medium')");
    await animationFrame();
    expect("img").not.toHaveClass("p-1");
    expect("img").toHaveClass("p-2");

    await click(".o-we-toolbar div[name='image_padding'] .dropdown-toggle");
    await animationFrame();
    await click(".o-dropdown--menu span:contains('Large')");
    await animationFrame();
    expect("img").not.toHaveClass("p-2");
    expect("img").toHaveClass("p-3");

    await click(".o-we-toolbar div[name='image_padding'] .dropdown-toggle");
    await animationFrame();
    await click(".o-dropdown--menu span:contains('XL')");
    await animationFrame();
    expect("img").not.toHaveClass("p-3");
    expect("img").toHaveClass("p-5");

    await click(".o-we-toolbar div[name='image_padding'] .dropdown-toggle");
    await animationFrame();
    await click(".o-dropdown--menu span:contains('None')");
    await animationFrame();
    expect("img").not.toHaveClass("p-5");
});

test("Can undo the image padding", async () => {
    const { editor } = await setupEditor(`
        <img class="img-fluid test-image" src="${base64Img}" alt="description" title="tooltip">
    `);
    await click("img.test-image");
    await waitFor(".o-we-toolbar");

    await click(".o-we-toolbar div[name='image_padding'] .dropdown-toggle");
    await animationFrame();
    await click(".o-dropdown--menu span:contains('Small')");
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
    await click(".o-we-toolbar div[name='image_modifiers'] button[name='image_transform']");
    await animationFrame();
    const transfoContainers = document.querySelectorAll(".transfo-container");
    expect(transfoContainers).toHaveCount(1);
    // The created transformation container is outside of the hoot fixture, clean it manually
    for (const transfoContainer of transfoContainers) {
        transfoContainer.remove();
    }
});

test("Image transform button is not available when config option is disabled", async () => {
    await setupEditor(`<img class="img-fluid test-image" src="${base64Img}">`, {
        config: { allowImageTransform: false },
    });
    await click("img.test-image");
    await waitFor(".o-we-toolbar");
    expect(".o-we-toolbar div[name='image_modifiers'] button[name='image_transform']").toHaveCount(
        0
    );
});

test("Image transformation dissapear when selection change", async () => {
    const { el } = await setupEditor(`
        <img class="img-fluid test-image" src="${base64Img}">
        <p> Hello world </p>
    `);
    await click("img.test-image");
    await waitFor(".o-we-toolbar");
    await click(".o-we-toolbar div[name='image_modifiers'] button[name='image_transform']");
    await animationFrame();
    let transfoContainers = document.querySelectorAll(".transfo-container");
    expect(transfoContainers).toHaveCount(1);

    setContent(
        el,
        `<img class="img-fluid test-image" src="/web/static/img/logo.png">
        <p> [Hello] world </p> `
    );
    await waitForNone(".transfo-container");
    transfoContainers = document.querySelectorAll(".transfo-container");
    expect(transfoContainers).toHaveCount(0);
    // Remove the transfoContainer element if not destroyed by the selection change
    for (const transfoContainer of transfoContainers) {
        transfoContainer.remove();
    }
});

test("Image transformation disappear on escape", async () => {
    await setupEditor(`
        <img class="img-fluid test-image" src="${base64Img}">
    `);
    click("img.test-image");
    await waitFor(".o-we-toolbar");
    let toolbar = document.querySelectorAll(".o-we-toolbar");
    expect(toolbar.length).toBe(1);
    click(".o-we-toolbar div[name='image_modifiers'] button[name='image_transform']");
    await animationFrame();
    toolbar = document.querySelectorAll(".o-we-toolbar");
    expect(toolbar.length).toBe(1);
    let transfoContainers = document.querySelectorAll(".transfo-container");
    expect(transfoContainers.length).toBe(1);
    press("escape");
    await animationFrame();
    transfoContainers = document.querySelectorAll(".transfo-container");
    expect(transfoContainers.length).toBe(0);
});

test("Image transformation disappears on backspace/delete", async () => {
    const { editor } = await setupEditor(`
        <img class="img-fluid test-image" src="${base64Img}">
    `);
    click("img.test-image");
    await expectElementCount(".o-we-toolbar", 1);
    await contains(
        ".o-we-toolbar div[name='image_modifiers'] button[name='image_transform']"
    ).click();
    await expectElementCount(".transfo-container", 1);
    press("backspace");
    await expectElementCount(".transfo-container", 0);
    await waitForNone(".o-we-toolbar[data-namespace='image']");
    undo(editor);
    click("img.test-image");
    await waitFor(".o-we-toolbar");
    await expectElementCount(".o-we-toolbar", 1);
    await contains(
        ".o-we-toolbar div[name='image_modifiers'] button[name='image_transform']"
    ).click();
    await expectElementCount(".transfo-container", 1);
    press("delete");
    await expectElementCount(".transfo-container", 0);
});

test("Image transformation disappears on character key press", async () => {
    const { editor } = await setupEditor(`
        <img class="img-fluid test-image" src="${base64Img}">
    `);
    click("img.test-image");
    await expectElementCount(".o-we-toolbar", 1);
    await contains(
        ".o-we-toolbar div[name='image_modifiers'] button[name='image_transform']"
    ).click();
    await expectElementCount(".transfo-container", 1);
    insertText(editor, "a");
    await expectElementCount(".transfo-container", 0);
});

test("Image transformation scalers position", async () => {
    await setupEditor(`
        <p><img class="img-fluid test-image" src="${base64Img}"></p>
    `);

    const checkScalersPositions = (image) => {
        const rect = image.getBoundingClientRect();
        const topValues = [rect.top, rect.top + rect.height / 2, rect.top + rect.height];
        const leftValues = [rect.left, rect.left + rect.width / 2, rect.left + rect.width];
        const vertical = "tmb";
        const horizontal = "lcr";
        for (let i = 0; i < 3; i++) {
            for (let j = 0; j < 3; j++) {
                if (i == 1 && j == 1) {
                    // no middle-center handler
                    continue;
                }
                const scaler = queryOne(`.transfo-scaler-${vertical[i]}${horizontal[j]}`);
                const scalerRect = scaler.getBoundingClientRect();
                expect(scalerRect.top + scalerRect.height / 2).toBe(topValues[i], { digits: 3 });
                expect(scalerRect.left + scalerRect.width / 2).toBe(leftValues[j], {
                    digits: 3,
                });
            }
        }
    };
    click("img.test-image");
    await expectElementCount(".o-we-toolbar", 1);
    click(".o-we-toolbar div[name='image_modifiers'] button[name='image_transform']");
    await animationFrame();
    await expectElementCount(".o-we-toolbar", 1);
    expect(".transfo-container").toHaveCount(1);
    checkScalersPositions(queryOne("img"));
    // resize by 25% update the position of the scalers
    await click(".o-we-toolbar [name='image_size'] .dropdown-toggle");
    await animationFrame();
    await click(".image_size_selector .dropdown-item:contains('25%')");
    await animationFrame();
    expect(".transfo-container").toHaveCount(0);
});

test("Image transformation reset", async () => {
    const { el } = await setupEditor(`
        <img class="img-fluid test-image" src="${base64Img}">
    `);
    el.querySelector("img").style.setProperty(
        "transform",
        "rotate(25deg) translateX(-0.2%) translateY(0.4%)"
    );
    const transformButtonSelector =
        ".o-we-toolbar div[name='image_modifiers'] button[name='image_transform']";
    const resetTransformButtonSelector =
        ".o-we-toolbar div[name='image_modifiers'] button[name='image_transform'].active";
    await click("img.test-image");
    await waitFor(".o-we-toolbar");

    expect(transformButtonSelector).toHaveCount(1);
    expect(resetTransformButtonSelector).toHaveCount(0);

    await click(transformButtonSelector);
    await animationFrame();
    expect(resetTransformButtonSelector).toHaveCount(1);

    await click(resetTransformButtonSelector);
    await animationFrame();
    expect(el.querySelector("img").style.getPropertyValue("transform")).toBe("");
    expect(transformButtonSelector).toHaveCount(1);
    expect(resetTransformButtonSelector).toHaveCount(0);
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

test("Deleting an image that is alone inside `p` should set selection at start of `p`", async () => {
    const { el } = await setupEditor(`<p><img>[]</p>`);
    await click("img");
    await waitFor('.o-we-toolbar[data-namespace="image"');
    expect("button[name='image_delete']").toHaveCount(1);
    await click("button[name='image_delete']");
    await animationFrame();
    expect(".test-image").toHaveCount(0);
    expect(getContent(el)).toBe(
        `<p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`
    );
});

test("Deleting an image that is the only content inside a <p> tag should place the selection at the start of the <p>", async () => {
    const { el } = await setupEditor(`<p>abc<img>[]</p>`);
    await click("img");
    await waitFor('.o-we-toolbar[data-namespace="image"');
    expect("button[name='image_delete']").toHaveCount(1);
    await click("button[name='image_delete']");
    await animationFrame();
    expect(".test-image").toHaveCount(0);
    expect(getContent(el)).toBe(`<p>abc[]</p>`);
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
    expect(img.parentElement.tagName).toBe("DIV");
});

test("can remove the link of an image", async () => {
    await setupEditor(`
        <a href="http://test.test/"><img src="${base64Img}"></a>
    `);
    const img = queryOne("img");
    await click("img");
    await waitFor(".o-we-toolbar");
    expect("button[name='unlink']").toHaveCount(1);
    await click("button[name='unlink']");
    await animationFrame();
    expect(img.parentElement.tagName).toBe("DIV");
    await expectElementCount(".o-we-linkpopover", 0);
});

test("can undo link removing of an image", async () => {
    const { editor } = await setupEditor(`
        <a href="http://test.test/"><img src="${base64Img}"></a>
    `);
    const img = queryOne("img");
    await click("img");
    await waitFor(".o-we-toolbar");
    await click("button[name='unlink']");
    await animationFrame();
    expect(img.parentElement.tagName).toBe("DIV");

    undo(editor);
    await animationFrame();
    expect(img.parentElement.tagName).toBe("A");
});

test("image toolbar should open on click even if selection is not in editable", async () => {
    const { el, editor } = await setupEditor(`
        <img src="${base64Img}">
    `);

    el.focus();
    moveSelectionOutsideEditor();
    const selectionData = editor.shared.selection.getSelectionData();
    expect(document.activeElement).toBe(el);
    expect(selectionData.documentSelectionIsInEditable).toBe(false);
    await pointerUp("img");
    await expectElementCount(".o-we-toolbar", 1);
});

test.tags("desktop");
test("Preview an image on dblclick", async () => {
    await setupEditor(`
        <img class="img-fluid test-image" src="${base64Img}">
    `);
    await dblclick("img.test-image");
    await animationFrame();
    expect(".o-FileViewer").toHaveCount(1);
});

test("should select image on pointerdown", async () => {
    const { plugins } = await setupEditor(`
        <img src="${base64Img}">
        <p>test[]</p>
    `);

    const imgElement = document.querySelector("img");
    await manuallyDispatchProgrammaticEvent(imgElement, "pointerdown");
    await animationFrame();

    const selectionPlugin = plugins.get("selection");
    const selectedNode = selectionPlugin.getTargetedNodes()[0];

    expect(selectedNode.tagName).toBe("IMG");
});
