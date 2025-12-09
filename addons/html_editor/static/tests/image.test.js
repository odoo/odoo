import { expect, test } from "@odoo/hoot";
import { click, dblclick, pointerUp, queryOne, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { contains } from "@web/../tests/web_test_helpers";
import { base64Img, setupEditor } from "./_helpers/editor";
import { getContent, moveSelectionOutsideEditor } from "./_helpers/selection";
import { undo } from "./_helpers/user_actions";
import { expectElementCount } from "./_helpers/ui_expectations";

test("Can change an image size", async () => {
    await setupEditor(`
        <img class="img-fluid test-image" src="${base64Img}">
    `);
    await click("img.test-image");
    await waitFor(".o-we-toolbar");
    expect(queryOne("img").style.width).toBe("");

    await click(".o-we-toolbar .dropdown-toggle[title='Resize image']");
    await animationFrame();
    await click(".image_size_selector .dropdown-item:contains('100%')");
    expect(queryOne("img").style.width).toBe("100%");

    await click(".o-we-toolbar .dropdown-toggle[title='Resize image']");
    await animationFrame();
    await click(".image_size_selector .dropdown-item:contains('50%')");
    expect(queryOne("img").style.width).toBe("50%");

    await click(".o-we-toolbar .dropdown-toggle[title='Resize image']");
    await animationFrame();
    await click(".image_size_selector .dropdown-item:contains('25%')");
    expect(queryOne("img").style.width).toBe("25%");

    await click(".o-we-toolbar .dropdown-toggle[title='Resize image']");
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

    await click(".o-we-toolbar .dropdown-toggle[title='Resize image']");
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

test("Deleting an image that is alone inside `p` should set selection at start of `p`", async () => {
    const { el } = await setupEditor(`<p><img>[]</p>`);
    await click("img");
    await waitFor(".o-we-toolbar");
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
    await waitFor(".o-we-toolbar");
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

test("image alignment option should not be available for non-table images", async () => {
    await setupEditor(`
        <p><img class="img-fluid test-image" src="${base64Img}"></p>
    `);
    await click("img.test-image");
    await waitFor(".o-we-toolbar");
    expect("button[title='Set image alignment']").toHaveCount(0);
});

test("image alignment option should be available for table images", async () => {
    await setupEditor(`
        <table class="table table-bordered o_table">
            <tbody>
                <tr>
                    <td><img class="img-fluid test-image" src="${base64Img}"></td>
                </tr>
            </tbody>
        </table>
    `);
    await click("img.test-image");
    await waitFor(".o-we-toolbar");
    expect("button[title='Set image alignment']").toHaveCount(1);
});

test("change image's alignment inside a table to 'Wrap text'", async () => {
    await setupEditor(`
        <table class="table table-bordered o_table">
            <tbody>
                <tr>
                    <td><img class="img-fluid test-image" src="${base64Img}"></td>
                </tr>
            </tbody>
        </table>
    `);
    await click("img.test-image");
    await waitFor(".o-we-toolbar");

    await click("button[title='Set image alignment']");
    await animationFrame();
    await click(".o_popover .btn[title='Wrap text']");
    await animationFrame();

    expect("img").toHaveClass("me-1 float-start");
});

test("change image's alignment inside a table to 'Break text'", async () => {
    await setupEditor(`
        <table class="table table-bordered o_table">
            <tbody>
                <tr>
                    <td><img class="img-fluid test-image" src="${base64Img}"></td>
                </tr>
            </tbody>
        </table>
    `);
    await click("img.test-image");
    await waitFor(".o-we-toolbar");

    await click("button[title='Set image alignment']");
    await animationFrame();
    await click(".o_popover .btn[title='Break text']");
    await animationFrame();

    expect("img").toHaveClass("d-block");
});

test("change image's alignment inside a table to 'Wrap text' then 'Break text' then 'Inline'", async () => {
    await setupEditor(`
        <table class="table table-bordered o_table">
            <tbody>
                <tr>
                    <td><img class="img-fluid test-image" src="${base64Img}"></td>
                </tr>
            </tbody>
        </table>
    `);
    await click("img.test-image");
    await waitFor(".o-we-toolbar");

    await click("button[title='Set image alignment']");
    await animationFrame();
    await click(".o_popover .btn[title='Wrap text']");
    await animationFrame();
    expect("img").toHaveClass("me-1 float-start");
    expect("img").not.toHaveClass("d-block");

    await click(".o_popover .btn[title='Break text']");
    await animationFrame();
    expect("img").not.toHaveClass("me-1 float-start");
    expect("img").toHaveClass("d-block");

    await click(".o_popover .btn[title='Inline']");
    await animationFrame();
    expect("img").not.toHaveClass("me-1 float-start");
    expect("img").not.toHaveClass("d-block");
    expect("img").toHaveClass("img-fluid test-image");
});

test("changing image alignment should not remove any existing classes", async () => {
    await setupEditor(`
        <table class="table table-bordered o_table">
            <tbody>
                <tr>
                    <td><img class="img-fluid test-image p-2" src="${base64Img}"></td>
                </tr>
            </tbody>
        </table>
    `);
    await click("img.test-image");
    await waitFor(".o-we-toolbar");

    await click("button[title='Set image alignment']");
    await animationFrame();
    await click(".o_popover .btn[title='Wrap text']");
    await animationFrame();

    expect("img").toHaveClass("p-2");
    expect("img").toHaveClass("me-1 float-start");
});
