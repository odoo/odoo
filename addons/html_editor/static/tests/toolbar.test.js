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
import { Plugin } from "../src/plugin";
import { MAIN_PLUGINS } from "../src/plugin_sets";
import { setupEditor } from "./_helpers/editor";
import { unformat } from "./_helpers/format";
import { getContent, moveSelectionOutsideEditor, setContent } from "./_helpers/selection";
import { convertNumericToUnit, getCSSVariableValue, getHtmlStyle } from "../src/utils/formatting";
import { fontSizeItems } from "../src/main/font/font_plugin";

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
    moveSelectionOutsideEditor();
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

test("toolbar link buttons react to selection change", async () => {
    const { el } = await setupEditor("<p>th[is is a] <a>link</a> test!</p>");

    await waitFor(".o-we-toolbar");
    expect(".btn[name='link']").toHaveCount(1);
    expect(".btn[name='link']").not.toHaveClass("active");
    expect(".btn[name='unlink']").toHaveCount(0);

    setContent(el, "<p>th[is is a <a>li]nk</a> test!</p>");
    await animationFrame();
    expect(".btn[name='link']").toHaveCount(1);
    expect(".btn[name='link']").toHaveClass("active");
    expect(".btn[name='unlink']").toHaveCount(1);

    setContent(el, "<p>th[is is a <a>link</a> tes]t!</p>");
    await animationFrame();
    expect(".btn[name='link']").toHaveCount(1);
    expect(".btn[name='link']").not.toHaveClass("active");
    expect(".btn[name='unlink']").toHaveCount(1);
});

test("toolbar works: can select font", async () => {
    const { el } = await setupEditor("<p>test</p>");
    expect(getContent(el)).toBe("<p>test</p>");

    // set selection to open toolbar
    expect(".o-we-toolbar").toHaveCount(0);
    setContent(el, "<p>[test]</p>");
    await waitFor(".o-we-toolbar");
    expect(".o-we-toolbar [name='typo']").toHaveText("Normal");

    await contains(".o-we-toolbar [name='typo'] .dropdown-toggle").click();
    await contains(".o_toolbar_item_selector_menu .dropdown-item:contains('Header 2')").click();
    expect(getContent(el)).toBe("<h2>[test]</h2>");
    expect(".o-we-toolbar [name='typo']").toHaveText("Header 2");
});

test("toolbar works: can select font size", async () => {
    const { el } = await setupEditor("<p>test</p>");
    expect(getContent(el)).toBe("<p>test</p>");
    const style = getHtmlStyle(document);
    const getFontSizeFromVar = (cssVar) => {
        const strValue = getCSSVariableValue(cssVar, style);
        const remValue = parseFloat(strValue);
        const pxValue = convertNumericToUnit(remValue, "rem", "px", style);
        return Math.round(pxValue);
    };

    // set selection to open toolbar
    expect(".o-we-toolbar").toHaveCount(0);
    setContent(el, "<p>[test]</p>");
    await waitFor(".o-we-toolbar");
    expect(".o-we-toolbar [name='size']").toHaveText(
        getFontSizeFromVar("body-font-size").toString()
    );

    await contains(".o-we-toolbar [name='size'] .dropdown-toggle").click();
    const sizes = new Set(
        fontSizeItems.map((item) => {
            return getFontSizeFromVar(item.variableName).toString();
        })
    );
    expect(queryAllTexts(".o_toolbar_item_selector_menu .dropdown-item")).toEqual([...sizes]);
    const h1Size = getFontSizeFromVar("h1-font-size").toString();
    await contains(`.o_toolbar_item_selector_menu .dropdown-item:contains('${h1Size}')`).click();
    expect(getContent(el)).toBe(`<p><span class="h1-fs">[test]</span></p>`);
    expect(".o-we-toolbar [name='size']").toHaveText(h1Size);
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

test("toolbar correctly show namespace button group and stop showing when namespace change", async () => {
    class TestPlugin extends Plugin {
        static name = "TestPlugin";
        static resources(p) {
            return {
                toolbarNamespace: [
                    {
                        id: "aNamespace",
                        isApplied: (nodeList) => {
                            return !!nodeList.find((node) => node.tagName === "DIV");
                        },
                    },
                ],
                toolbarCategory: { id: "test_group", sequence: 24, namespace: "aNamespace" },
                toolbarItems: [
                    {
                        id: "test_btn",
                        category: "test_group",
                        name: "Test Button",
                        icon: "fa-square",
                    },
                ],
            };
        }
    }
    const { el } = await setupEditor("<div>[<section><p>abc</p></section><div>d]ef</div></div>", {
        config: { Plugins: [...MAIN_PLUGINS, TestPlugin] },
    });
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='test_group']").toHaveCount(1);
    setContent(el, "<div><section><p>[abc]</p></section><div>def</div></div>");
    await animationFrame();
    expect(".btn-group[name='test_group']").toHaveCount(0);
});

test("toolbar correctly process inheritance buttons chain", async () => {
    class TestPlugin extends Plugin {
        static name = "TestPlugin";
        static resources(p) {
            return {
                toolbarCategory: { id: "test_group" },
                toolbarItems: [
                    {
                        id: "test_btn",
                        category: "test_group",
                        name: "Test Button",
                        icon: "fa-square",
                    },
                    {
                        id: "test_btn2",
                        category: "test_group",
                        inherit: "test_btn",
                        name: "Test Button 2",
                    },
                ],
            };
        }
    }
    await setupEditor("<p>[abc]</p>", {
        config: { Plugins: [...MAIN_PLUGINS, TestPlugin] },
    });
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='test_group']").toHaveCount(1);
    expect("button[name='test_btn']").toHaveCount(1);
    expect("button[name='test_btn'] span.fa").toHaveClass("fa-square");
    expect("button[name='test_btn']").toHaveAttribute("title", "Test Button");

    expect("button[name='test_btn2']").toHaveCount(1);
    expect("button[name='test_btn2'] span.fa").toHaveClass("fa-square");
    expect("button[name='test_btn2']").toHaveAttribute("title", "Test Button 2");
});

test("toolbar does not evaluate isFormatApplied when namespace does not match", async () => {
    class TestPlugin extends Plugin {
        static name = "TestPlugin";
        static resources(p) {
            return {
                toolbarCategory: { id: "test_group", sequence: 24, namespace: "image" },
                toolbarItems: [
                    {
                        id: "test_btn",
                        category: "test_group",
                        action(dispatch) {
                            dispatch("test_cmd");
                        },
                        name: "Test Button",
                        icon: "fa-square",
                        isFormatApplied: () => expect.step("image format evaluated"),
                    },
                ],
            };
        }
    }
    await setupEditor(
        `
        <div>
            <p>[Foo]</p>
            <img class="img-fluid" src="/web/static/img/logo.png">
        </div>
    `,
        {
            config: { Plugins: [...MAIN_PLUGINS, TestPlugin] },
        }
    );
    await waitFor(".o-we-toolbar");
    expect.verifySteps([]);
    click("img");
    await animationFrame();
    expect.verifySteps(["image format evaluated"]);
});

test("plugins can create buttons with text in toolbar", async () => {
    class TestPlugin extends Plugin {
        static name = "TestPlugin";
        static resources(p) {
            return {
                toolbarCategory: { id: "test_group", sequence: 24 },
                toolbarItems: [
                    {
                        id: "test_btn",
                        category: "test_group",
                        action(dispatch) {
                            dispatch("test_cmd");
                        },
                        name: "Test Button",
                        text: "Text button",
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

test("toolbar buttons should have rounded corners at the edges of a group", async () => {
    await setupEditor("<p>[test]</p>");
    await waitFor(".o-we-toolbar");
    const buttonGroups = queryAll(".o-we-toolbar .btn-group");
    for (const group of buttonGroups) {
        for (let i = 0; i < group.children.length; i++) {
            const button = group.children[i];
            const computedStyle = getComputedStyle(button);
            const borderRadius = Object.fromEntries(
                ["top-left", "top-right", "bottom-left", "bottom-right"].map((corner) => [
                    corner,
                    Number.parseInt(computedStyle[`border-${corner}-radius`]),
                ])
            );
            // Should have rounded corners on the left only if first button
            if (i === 0) {
                expect(borderRadius["top-left"]).toBeGreaterThan(0);
                expect(borderRadius["bottom-left"]).toBeGreaterThan(0);
            } else {
                expect(borderRadius["top-left"]).toBe(0);
                expect(borderRadius["bottom-left"]).toBe(0);
            }
            // Should have rounded corners on the right only if last button
            if (i === group.children.length - 1) {
                expect(borderRadius["top-right"]).toBeGreaterThan(0);
                expect(borderRadius["bottom-right"]).toBeGreaterThan(0);
            } else {
                expect(borderRadius["top-right"]).toBe(0);
                expect(borderRadius["bottom-right"]).toBe(0);
            }
        }
    }
});
