import { expect, test } from "@odoo/hoot";
import {
    click,
    press,
    queryAll,
    queryAllTexts,
    waitFor,
    waitForNone,
    waitUntil,
} from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { contains } from "@web/../tests/web_test_helpers";
import { setupEditor } from "./_helpers/editor";
import { unformat } from "./_helpers/format";
import { getContent, setContent, setSelection } from "./_helpers/selection";
import { Plugin } from "../src/plugin";
import { MAIN_PLUGINS } from "../src/plugin_sets";

test("toolbar is only visible when selection is not collapsed", async () => {
    const { el } = await setupEditor("<p>test</p>");

    // set a non-collapsed selection to open toolbar
    expect(".o-we-toolbar").toHaveCount(0);
    setContent(el, "<p>[test]</p>");
    await waitFor(".o-we-toolbar");
    expect(".o-we-toolbar").toHaveCount(1);

    // set a collapsed selection to close toolbar
    setContent(el, "<p>test[]</p>");
    await waitUntil(() => !document.querySelector(".o-we-toolbar"));
    expect(".o-we-toolbar").toHaveCount(0);
});

test("toolbar closes when selection leaves editor", async () => {
    await setupEditor("<p>[test]</p>");
    await waitFor(".o-we-toolbar");

    click(document.body);
    setSelection({
        anchorNode: document.body,
        anchorOffset: 0,
        focusNode: document.body,
        focusOffset: 0,
    });
    await waitForNone(".o-we-toolbar");
    expect(".o-we-toolbar").toHaveCount(0);
});

test("toolbar works: can format bold", async () => {
    const { el } = await setupEditor("<p>test</p>");
    expect(getContent(el)).toBe("<p>test</p>");

    // set selection to open toolbar
    expect(".o-we-toolbar").toHaveCount(0);
    setContent(el, "<p>[test]</p>");
    await waitFor(".o-we-toolbar");

    // click on toggle bold
    await contains(".btn[name='bold']").click();
    expect(getContent(el)).toBe("<p><strong>[test]</strong></p>");
});

test.tags("iframe")("toolbar in an iframe works: can format bold", async () => {
    const { el } = await setupEditor("<p>test</p>", { props: { iframe: true } });
    expect("iframe").toHaveCount(1);
    expect(getContent(el)).toBe("<p>test</p>");

    // set selection to open toolbar
    expect(".o-we-toolbar").toHaveCount(0);
    setContent(el, "<p>[test]</p>");
    await waitFor(".o-we-toolbar");

    // click on toggle bold
    await contains(".btn[name='bold']").click();
    expect(getContent(el)).toBe("<p><strong>[test]</strong></p>");
});

test("toolbar buttons react to selection change", async () => {
    const { el } = await setupEditor("<p>test some text</p>");

    // set selection to open toolbar
    setContent(el, "<p>[test] some text</p>");
    await waitFor(".o-we-toolbar");

    // check that bold button is not active
    expect(".btn[name='bold']").not.toHaveClass("active");

    // click on toggle bold
    await contains(".btn[name='bold']").click();
    expect(getContent(el)).toBe("<p><strong>[test]</strong> some text</p>");
    expect(".btn[name='bold']").toHaveClass("active");

    // set selection where text is not bold
    setContent(el, "<p><strong>test</strong> some [text]</p>");
    await waitFor(".btn[name='bold']:not(.active)");
    expect(".btn[name='bold']").not.toHaveClass("active");

    // set selection again where text is bold
    setContent(el, "<p><strong>[test]</strong> some text</p>");
    await waitFor(".btn[name='bold'].active");
    expect(".btn[name='bold']").toHaveClass("active");
});

test("toolbar buttons react to selection change (2)", async () => {
    const { el } = await setupEditor("<p><strong>test [some]</strong> some text</p>");

    await waitFor(".o-we-toolbar");
    expect(".btn[name='bold']").toHaveClass("active");

    // extends selection to include non-bold text
    setContent(el, "<p><strong>test [some</strong> some] text</p>");
    // @todo @phoenix: investigate why waiting for animation frame is (sometimes) not enough
    await waitFor(".btn[name='bold']:not(.active)");
    expect(".btn[name='bold']").not.toHaveClass("active");

    // change selection to come back into bold text
    setContent(el, "<p><strong>test [so]me</strong> some text</p>");
    await waitFor(".btn[name='bold'].active");
    expect(".btn[name='bold']").toHaveClass("active");
});

test("toolbar list buttons react to selection change", async () => {
    const { el } = await setupEditor("<ul><li>[abc]</li></ul>");

    await waitFor(".o-we-toolbar");
    expect(".btn[name='bulleted_list']").toHaveClass("active");
    expect(".btn[name='numbered_list']").not.toHaveClass("active");
    expect(".btn[name='checklist']").not.toHaveClass("active");

    // Toggle to numbered list
    click(".btn[name='numbered_list']");
    await waitFor(".btn[name='numbered_list'].active");
    expect(getContent(el)).toBe("<ol><li>[abc]</li></ol>");
    expect(".btn[name='bulleted_list']").not.toHaveClass("active");
    expect(".btn[name='numbered_list']").toHaveClass("active");
    expect(".btn[name='checklist']").not.toHaveClass("active");

    // Toggle to checklist
    click(".btn[name='checklist']");
    await waitFor(".btn[name='checklist'].active");
    expect(getContent(el)).toBe('<ul class="o_checklist"><li>[abc]</li></ul>');
    expect(".btn[name='bulleted_list']").not.toHaveClass("active");
    expect(".btn[name='numbered_list']").not.toHaveClass("active");
    expect(".btn[name='checklist']").toHaveClass("active");

    // Toggle list off
    click(".btn[name='checklist']");
    await waitFor(".btn[name='checklist']:not(.active)");
    expect(getContent(el)).toBe("<p>[abc]</p>");
    expect(".btn[name='bulleted_list']").not.toHaveClass("active");
    expect(".btn[name='numbered_list']").not.toHaveClass("active");
    expect(".btn[name='checklist']").not.toHaveClass("active");
});

test("toolbar works: can select font", async () => {
    const { el } = await setupEditor("<p>test</p>");
    expect(getContent(el)).toBe("<p>test</p>");

    // set selection to open toolbar
    expect(".o-we-toolbar").toHaveCount(0);
    setContent(el, "<p>[test]</p>");
    await waitFor(".o-we-toolbar");
    expect(".o-we-toolbar [name='font']").toHaveText("Normal");

    await contains(".o-we-toolbar [name='font'] .dropdown-toggle").click();
    await contains(".o_font_selector_menu .dropdown-item:contains('Header 2')").click();
    expect(getContent(el)).toBe("<h2>[test]</h2>");
    expect(".o-we-toolbar [name='font']").toHaveText("Header 2");
});

test("toolbar works: can select font size", async () => {
    const { el } = await setupEditor("<p>test</p>");
    expect(getContent(el)).toBe("<p>test</p>");

    // set selection to open toolbar
    expect(".o-we-toolbar").toHaveCount(0);
    setContent(el, "<p>[test]</p>");
    await waitFor(".o-we-toolbar");
    expect(".o-we-toolbar [name='font-size']").toHaveText("14");

    await contains(".o-we-toolbar [name='font-size'] .dropdown-toggle").click();
    const items = ["80", "72", "64", "56", "28", "21", "18", "17", "15", "14", "13"];
    expect(queryAllTexts(".o_font_selector_menu .dropdown-item")).toEqual(items);

    await contains(".o_font_selector_menu .dropdown-item:contains('28')").click();
    expect(getContent(el)).toBe(`<p><span class="h1-fs">[test]</span></p>`);
    expect(".o-we-toolbar [name='font-size']").toHaveText("28");
});

test("toolbar should not open on keypress tab inside table", async () => {
    const contentBefore = unformat(`
        <table>
            <tbody>
                <tr>
                    <td><p>[]ab</p></td>
                    <td><p>cd</p></td>
                </tr>
            </tbody>
        </table>
    `);
    const contentAfter = unformat(`
        <table>
            <tbody>
                <tr>
                    <td><p>ab</p></td>
                    <td><p>cd[]</p></td>
                </tr>
            </tbody>
        </table>
    `);

    const { el } = await setupEditor(contentBefore);
    press("Tab");
    expect(getContent(el)).toBe(contentAfter);
    await animationFrame();
    expect(".o-we-toolbar").toHaveCount(0);
});

test("toolbar should close on keypress tab inside table", async () => {
    const contentBefore = unformat(`
        <table>
            <tbody>
                <tr>
                    <td><p>[ab]</p></td>
                    <td><p>cd</p></td>
                </tr>
            </tbody>
        </table>
    `);
    const contentAfter = unformat(`
        <table>
            <tbody>
                <tr>
                    <td><p>ab</p></td>
                    <td><p>cd[]</p></td>
                </tr>
            </tbody>
        </table>
    `);

    const { el } = await setupEditor(contentBefore);
    await waitFor(".o-we-toolbar");
    press("Tab");
    expect(getContent(el)).toBe(contentAfter);
    await waitForNone(".o-we-toolbar");
    expect(".o-we-toolbar").toHaveCount(0);
});

test("toolbar buttons shouldn't be active without text node in the selection", async () => {
    await setupEditor("<div>[<p><br></p>]</div>");
    await waitFor(".o-we-toolbar");
    expect(queryAll(".o-we-toolbar .btn.active").length).toBe(0);
});

test("toolbar behave properly if selection has no range", async () => {
    const { el } = await setupEditor("<p>test</p>");

    expect(".o-we-toolbar").toHaveCount(0);
    setContent(el, "<p>[test]</p>");
    await waitFor(".o-we-toolbar");
    expect(".o-we-toolbar").toHaveCount(1);

    const selection = document.getSelection();
    selection.removeAllRanges();

    setContent(el, "<p>abc</p>");
    await waitUntil(() => !document.querySelector(".o-we-toolbar"));
    expect(".o-we-toolbar").toHaveCount(0);
});

test("toolbar shows namespaced button groups when the namespaced element is selected", async () => {
    await setupEditor(`
        <img class="img-fluid" src="/web/static/img/logo.png">
    `);
    await click("img");
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='image_shape']").toHaveCount(1);
});

test("toolbar stop showing namespaced button groups when namespaced element is unselected", async () => {
    const { el } = await setupEditor(`
        <div>
            <p>Foo</p>
            <img class="img-fluid" src="/web/static/img/logo.png">
        </div>
    `);
    await click("img");
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='image_shape']").toHaveCount(1);
    setContent(
        el,
        `
        <div>
            <p>[Foo]</p>
            <img class="img-fluid" src="/web/static/img/logo.png">
        </div>
    `
    );
    await animationFrame();
    expect(".btn-group[name='image_shape']").toHaveCount(0);
});

test("toolbar does not evaluate isFormatApplied when namespace does not match", async () => {
    class TestPlugin extends Plugin {
        static name = "TestPlugin";
        static resources(p) {
            return {
                toolbarGroup: [
                    {
                        id: "test_group",
                        sequence: 24,
                        namespace: "IMG",
                        buttons: [
                            {
                                id: "test_btn",
                                cmd: "test_cmd",
                                name: "Test Button",
                                icon: "fa-square",
                                isFormatApplied: () => expect.step("image format evaluated"),
                            },
                        ],
                    },
                ],
            };
        }
    }
    await setupEditor(
        `
        <div>
            <p>Foo</p>
            <img class="img-fluid" src="/web/static/img/logo.png">
        </div>
    `,
        {
            config: { Plugins: [...MAIN_PLUGINS, TestPlugin] },
        }
    );
    expect([]).toVerifySteps();
    click("img");
    await waitFor(".o-we-toolbar");
    expect(["image format evaluated"]).toVerifySteps();
});

test("plugins can create buttons with text in toolbar", async () => {
    class TestPlugin extends Plugin {
        static name = "TestPlugin";
        static resources(p) {
            return {
                toolbarGroup: [
                    {
                        id: "test_group",
                        sequence: 24,
                        buttons: [
                            {
                                id: "test_btn",
                                cmd: "test_cmd",
                                name: "Test Button",
                                text: "Text button",
                            },
                        ],
                    },
                ],
            };
        }
    }
    await setupEditor(`<div> <p class="foo">[Foo]</p> </div>`, {
        config: { Plugins: [...MAIN_PLUGINS, TestPlugin] },
    });
    await waitFor(".o-we-toolbar");
    expect("button[name='test_btn']").toHaveText("Text button");
});
