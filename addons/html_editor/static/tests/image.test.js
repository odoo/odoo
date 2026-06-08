import { expect, mockFetch, test } from "@odoo/hoot";
import {
    click,
    dblclick,
    queryOne,
    waitFor,
    manuallyDispatchProgrammaticEvent,
    queryAll,
} from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { contains } from "@web/../tests/web_test_helpers";
import { base64Img, setupEditor } from "./_helpers/editor";
import { getContent, moveSelectionOutsideEditor } from "./_helpers/selection";
import { undo } from "./_helpers/user_actions";
import { expectElementCount } from "./_helpers/ui_expectations";
import { getMimetype } from "@html_editor/utils/image";

test("image can be selected", async () => {
    const { plugins } = await setupEditor(`
        <img src="${base64Img}">
    `);

    await click("img");
    await waitFor(".o-we-toolbar");
    expect(".btn-group button[name='image_preview']").toHaveCount(1);
    const selectionPlugin = plugins.get("selection");
    expect(selectionPlugin.getTargetedNodes()[0].tagName).toBe("IMG");
});

test("Can change an image size", async () => {
    await setupEditor(`
        <img class="img-fluid test-image" src="${base64Img}">
    `);
    await click("img.test-image");
    await waitFor(".o-we-toolbar");
    expect(queryOne("img").style.width).toBe("");

    await click(".o-we-toolbar [name='image_actions'] .dropdown-toggle");
    await animationFrame();
    await click(".image_size_selector .dropdown-item:contains('100%')");
    expect(queryOne("img").style.width).toBe("100%");

    await click(".o-we-toolbar [name='image_actions'] .dropdown-toggle");
    await animationFrame();
    await click(".image_size_selector .dropdown-item:contains('50%')");
    expect(queryOne("img").style.width).toBe("50%");

    await click(".o-we-toolbar [name='image_actions'] .dropdown-toggle");
    await animationFrame();
    await click(".image_size_selector .dropdown-item:contains('25%')");
    expect(queryOne("img").style.width).toBe("25%");

    await click(".o-we-toolbar [name='image_actions'] .dropdown-toggle");
    await animationFrame();
    await click(".image_size_selector .dropdown-item:contains('Default')");
    expect(queryOne("img").style.width).toBe("");
});

test("image should show actual width if set to default size", async () => {
    await setupEditor(`
        <img src="${base64Img}" style="width: 50%;">
    `);
    await click("img");
    await waitFor(".o-we-toolbar");
    expect(queryOne(".o-we-toolbar .dropdown-toggle[title='Resize image']")).toHaveText("50%");
    await click(".o-we-toolbar .dropdown-toggle[title='Resize image']");
    await animationFrame();
    await click(".image_size_selector .dropdown-item:contains('Default')");
    await animationFrame();
    expect(queryOne(".o-we-toolbar .dropdown-toggle[title='Resize image']")).toHaveText(
        queryOne("img").getBoundingClientRect().width + "px"
    );
});

test("Can undo the image sizing", async () => {
    const { editor } = await setupEditor(`
        <img class="img-fluid test-image" src="${base64Img}">
    `);
    await click("img.test-image");
    await waitFor(".o-we-toolbar");

    await click(".o-we-toolbar [name='image_actions'] .dropdown-toggle");
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

    await click(".o-we-toolbar .dropdown-toggle[title='Set image padding']");
    await animationFrame();
    await click(".o-dropdown--menu span:contains('Small')");
    await animationFrame();
    expect("img").toHaveClass("p-1");

    await click(".o-we-toolbar .dropdown-toggle[title='Set image padding']");
    await animationFrame();
    await click(".o-dropdown--menu span:contains('Medium')");
    await animationFrame();
    expect("img").not.toHaveClass("p-1");
    expect("img").toHaveClass("p-2");

    await click(".o-we-toolbar .dropdown-toggle[title='Set image padding']");
    await animationFrame();
    await click(".o-dropdown--menu span:contains('Large')");
    await animationFrame();
    expect("img").not.toHaveClass("p-2");
    expect("img").toHaveClass("p-3");

    await click(".o-we-toolbar .dropdown-toggle[title='Set image padding']");
    await animationFrame();
    await click(".o-dropdown--menu span:contains('XL')");
    await animationFrame();
    expect("img").not.toHaveClass("p-3");
    expect("img").toHaveClass("p-5");

    await click(".o-we-toolbar .dropdown-toggle[title='Set image padding']");
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

    await click(".o-we-toolbar .dropdown-toggle[title='Set image padding']");
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

test("Can delete an image with display block style applied", async () => {
    await setupEditor(`
        <p><img class="img-fluid test-image d-block" src="${base64Img}"></p>
    `);
    await click("img");
    await expectElementCount(".o-we-toolbar button[name='image_delete']", 1);
    await click("button[name='image_delete']");
    await animationFrame();
    await expectElementCount(".test-image", 0);
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
    await click("img");
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

test("Correctly determine the mimetype of an image with wrong extension", async () => {
    const imgSrc = "/web/image/wrongExtension.jpeg";
    mockFetch((url) => {
        if (url === imgSrc) {
            return new Response("", { headers: new Headers([["content-Type", "image/png"]]) });
        }
    });
    const imageEl = document.createElement("img");
    imageEl.setAttribute("src", imgSrc);
    const mimetype = await getMimetype(imageEl);
    expect(mimetype).toBe("image/png");
});

test("image alignment option should be available for images", async () => {
    await setupEditor(`
        <p><img class="img-fluid test-image" src="${base64Img}"></p>
    `);
    await click("img.test-image");
    await waitFor(".o-we-toolbar");
    expectElementCount(".o-we-toolbar button[title='Set image alignment']", 1);
});

test("change image's alignment to 'Wrap text'", async () => {
    await setupEditor(`
        <p><img class="img-fluid" src="${base64Img}"></p>
    `);
    await click("img");
    await waitFor(".o-we-toolbar");
    await click(".o-we-toolbar button[title='Set image alignment']");
    await animationFrame();
    await click(".o-we-toolbar-dropdown .btn[title='Wrap text']");
    await animationFrame();
    expect("img").toHaveClass("float-start");
});

test("change image's alignment to 'Break text'", async () => {
    await setupEditor(`
        <p><img class="img-fluid" src="${base64Img}"></p>
    `);
    await click("img");
    await waitFor(".o-we-toolbar");
    await click(".o-we-toolbar button[title='Set image alignment']");
    await animationFrame();
    await click(".o-we-toolbar-dropdown .btn[title='Break text']");
    await animationFrame();
    expect("img").toHaveClass("d-block");
});

test("change image's alignment to 'Wrap text' then 'Break text' then 'Inline'", async () => {
    await setupEditor(`
        <p><img class="img-fluid" src="${base64Img}"></p>
    `);
    await click("img");
    await waitFor(".o-we-toolbar");
    await click(".o-we-toolbar button[title='Set image alignment']");
    await animationFrame();
    await click(".o-we-toolbar-dropdown .btn[title='Wrap text']");
    await animationFrame();
    expect("img").toHaveClass("float-start");
    expect("img").not.toHaveClass("d-block");

    await click(".o-we-toolbar button[title='Set image alignment']");
    await animationFrame();
    await click(".o-we-toolbar-dropdown .btn[title='Break text']");
    await animationFrame();
    expect("img").not.toHaveClass("float-start");
    expect("img").toHaveClass("d-block");

    await click(".o-we-toolbar button[title='Set image alignment']");
    await animationFrame();
    await click(".o-we-toolbar-dropdown .btn[title='Inline']");
    await animationFrame();
    expect("img").not.toHaveClass("float-start");
    expect("img").not.toHaveClass("d-block");
    expect("img").toHaveClass("img-fluid");
});

test("changing image alignment should not remove any existing classes", async () => {
    await setupEditor(`
        <p><img class="img-fluid p-2" src="${base64Img}"></p>
    `);
    await click("img");
    await waitFor(".o-we-toolbar");
    await click(".o-we-toolbar button[title='Set image alignment']");
    await animationFrame();
    await click(".o-we-toolbar-dropdown .btn[title='Wrap text']");
    await animationFrame();
    expect("img").toHaveClass("p-2 img-fluid float-start");
});

test("test order of image options in image toolbar", async () => {
    await setupEditor(`<img src="${base64Img}">`);
    await click("img");
    await waitFor(".o-we-toolbar");

    const toolbarGroups = queryAll(".o-we-toolbar .btn-group");
    expect(toolbarGroups).toHaveCount(5);
    expect(toolbarGroups.map((g) => g.getAttribute("name"))).toEqual([
        "image_modifiers",
        "image_actions",
        "image_link",
        "image_replace",
        "image_delete",
    ]);

    expect(
        queryAll(".o-we-toolbar .btn-group[name='image_modifiers'] .btn").map((b) =>
            b.getAttribute("title")
        )
    ).toMatchObject(["Set image alignment", "Set image padding", "Crop image"]);

    expect(
        queryAll(".o-we-toolbar .btn-group[name='image_actions'] .btn").map((b) =>
            b.getAttribute("title")
        )
    ).toMatchObject(["Resize image", "Preview image"]);
});
