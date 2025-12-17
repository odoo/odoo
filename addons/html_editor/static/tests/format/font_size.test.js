import { test, expect } from "@odoo/hoot";
import { setupEditor, testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { setFontSize, tripleClick } from "../_helpers/user_actions";
import { Plugin } from "@html_editor/plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { animationFrame } from "@odoo/hoot-mock";
import { execCommand } from "../_helpers/userCommands";
import { press } from "@odoo/hoot-dom";
import { getContent } from "../_helpers/selection";

test("should change the font size of a few characters", async () => {
    await testEditor({
        contentBefore: "<p>ab[cde]fg</p>",
        stepFunction: setFontSize("10px"),
        contentAfter: '<p>ab<span style="font-size: 10px;">[cde]</span>fg</p>',
    });
});

test("should change the font size the qweb tag", async () => {
    await testEditor({
        contentBefore: `<div><p t-esc="'Test'" contenteditable="false">[Test]</p></div>`,
        stepFunction: setFontSize("36px"),
        contentAfter: `<div>[<p t-esc="'Test'" contenteditable="false" style="font-size: 36px;">Test</p>]</div>`,
    });
});

test("should change the font size of a whole heading after a triple click", async () => {
    await testEditor({
        contentBefore: "<h1>[ab</h1><p>]cd</p>",
        stepFunction: async (editor) => {
            await tripleClick(editor.editable.querySelector("h1"));
            setFontSize("36px")(editor);
        },
        contentAfter: '<h1><span style="font-size: 36px;">[ab]</span></h1><p>cd</p>',
    });
});

test("should get ready to type with a different font size", async () => {
    const { editor } = await setupEditor('<p class="p">ab[]cd</p>');
    execCommand(editor, "formatFontSize", { size: "36px" });
    await animationFrame();
    expect(".p span").toHaveStyle({ "font-size": "36px" });
    expect(".p span").toHaveAttribute("data-oe-zws-empty-inline", "");
});

test("should change the font-size for a character in an inline that has a font-size", async () => {
    await testEditor({
        contentBefore: `<p>a<span style="font-size: 10px;">b[c]d</span>e</p>`,
        stepFunction: setFontSize("20px"),
        contentAfter: unformat(`<p>
                            a
                            <span style="font-size: 10px;">b</span>
                            <span style="font-size: 20px;">[c]</span>
                            <span style="font-size: 10px;">d</span>
                            e
                        </p>`),
    });
});

test("should change the font-size of a character with multiples inline ancestors having a font-size", async () => {
    await testEditor({
        contentBefore: unformat(`<p>
                            a
                            <span style="font-size: 10px;">
                                b
                                <span style="font-size: 20px;">c[d]e</span>
                                f
                            </span>
                            g
                        </p>`),
        stepFunction: setFontSize("30px"),
        contentAfter: unformat(`<p>
                            a
                            <span style="font-size: 10px;">
                                b
                                <span style="font-size: 20px;">c</span>
                            </span>
                            <span style="font-size: 30px;">[d]</span>
                            <span style="font-size: 10px;">
                                <span style="font-size: 20px;">e</span>
                                f
                            </span>
                            g
                        </p>`),
    });
});

test("should remove a redundant font-size", async () => {
    await testEditor({
        contentBefore: '<p style="font-size: 10px">b<span style="font-size: 10px;">[c]</span>d</p>',
        stepFunction: setFontSize("10px"),
        contentAfter: '<p style="font-size: 10px">b[c]d</p>',
    });
});

test("should change the font-size to default", async () => {
    await testEditor({
        contentBefore: "<p>[ab]</p>",
        stepFunction: setFontSize(),
        contentAfter: "<p>[ab]</p>",
    });
});

test("should change the font-size to default removing the existing style with no empty span at the end", async () => {
    await testEditor({
        contentBefore: '<p><span style="font-size: 36px;">[abc]</span></p>',
        stepFunction: setFontSize(),
        contentAfter: "<p>[abc]</p>",
    });
});
test("should not format non-editable text (setFontSize)", async () => {
    await testEditor({
        contentBefore: '<p>a[b</p><p contenteditable="false">c</p><p>d]e</p>',
        stepFunction: setFontSize("10px"),
        contentAfter: unformat(`
            <p>a<span style="font-size: 10px;">[b</span></p>
            <p contenteditable="false">c</p>
            <p><span style="font-size: 10px;">d]</span>e</p>
        `),
    });
});

test("should add font size in selected table cells", async () => {
    await testEditor({
        contentBefore:
            '<table><tbody><tr><td class="o_selected_td"><p>[<br></p></td><td class="o_selected_td"><p><br></p>]</td></tr><tr><td><p><br></p></td><td><p><br></p></td></tr></tbody></table>',
        stepFunction: setFontSize("48px"),
        contentAfter:
            '<table><tbody><tr><td><p><span style="font-size: 48px;">[<br></span></p></td><td><p><span style="font-size: 48px;">]<br></span></p></td></tr><tr><td><p><br></p></td><td><p><br></p></td></tr></tbody></table>',
    });
});

test("should add font size in all table cells", async () => {
    await testEditor({
        contentBefore:
            '<table><tbody><tr><td class="o_selected_td"><p>[<br></p></td><td class="o_selected_td"><p><br></p></td></tr><tr><td class="o_selected_td"><p><br></p></td><td class="o_selected_td"><p><br>]</p></td></tr></tbody></table>',
        stepFunction: setFontSize("36px"),
        contentAfter:
            '<table><tbody><tr><td><p><span style="font-size: 36px;">[<br></span></p></td><td><p><span style="font-size: 36px;"><br></span></p></td></tr><tr><td><p><span style="font-size: 36px;"><br></span></p></td><td><p><span style="font-size: 36px;">]<br></span></p></td></tr></tbody></table>',
    });
});

test("should add font size in selected table cells with h1 as first child", async () => {
    await testEditor({
        contentBefore:
            '<table><tbody><tr><td class="o_selected_td"><h1>[<br></h1></td><td class="o_selected_td"><h1><br>]</h1></td></tr><tr><td><h1><br></h1></td><td><h1><br></h1></td></tr></tbody></table>',
        stepFunction: setFontSize("18px"),
        contentAfter:
            '<table><tbody><tr><td><h1><span style="font-size: 18px;">[<br></span></h1></td><td><h1><span style="font-size: 18px;">]<br></span></h1></td></tr><tr><td><h1><br></h1></td><td><h1><br></h1></td></tr></tbody></table>',
    });
});

test("should apply font size in unbreakable span with class", async () => {
    await testEditor({
        contentBefore: `<h1><span class="oe_unbreakable">some [text]</span></h1>`,
        stepFunction: setFontSize("18px"),
        contentAfter: `<h1><span class="oe_unbreakable">some <span style="font-size: 18px;">[text]</span></span></h1>`,
    });
});

test("should apply font size in unbreakable span without class", async () => {
    class AddUnsplittableRulePlugin extends Plugin {
        static id = "addUnsplittableRule";
        resources = {
            unsplittable_node_predicates: (node) => node.getAttribute?.("t") === "unbreakable",
        };
    }
    await testEditor({
        contentBefore: `<h1><span t="unbreakable">some [text]</span></h1>`,
        stepFunction: setFontSize("18px"),
        contentAfter: `<h1><span t="unbreakable">some <span style="font-size: 18px;">[text]</span></span></h1>`,
        config: { Plugins: [...MAIN_PLUGINS, AddUnsplittableRulePlugin] },
    });
});

test("should add style to a span parent of an inline", async () => {
    await testEditor({
        contentBefore: `<p>a<span style="background-color: black;"><strong>[bc]</strong></span>d</p>`,
        stepFunction: setFontSize("10px"),
        contentAfter: `<p>a<span style="background-color: black; font-size: 10px;"><strong>[bc]</strong></span>d</p>`,
    });
});

test("should apply font size on top of `u` and `s` tags", async () => {
    await testEditor({
        contentBefore: `<p>a<u>[b]</u>c</p>`,
        stepFunction: setFontSize("18px"),
        contentAfter: `<p>a<span style="font-size: 18px;"><u>[b]</u></span>c</p>`,
    });
});

test("should apply font size on topmost `u` or `s` tags if multiple applied", async () => {
    await testEditor({
        contentBefore: `<p>a<s><u>[b]</u></s>c</p>`,
        stepFunction: setFontSize("18px"),
        contentAfter: `<p>a<span style="font-size: 18px;"><s><u>[b]</u></s></span>c</p>`,
    });
});

test("should add style to br except line-break br", async () => {
    const { editor, el } = await setupEditor("<p>[]abc<br><br></p>");
    await press(["ctrl", "a"]);
    execCommand(editor, "formatFontSize", { size: "36px" });
    expect(getContent(el)).toBe(`<p><span style="font-size: 36px;">[abc]</span><br><br></p>`);
});

test("should add style to br except line-break br (2)", async () => {
    const { editor, el } = await setupEditor("<p>[]abc<br><br><br></p>");
    await press(["ctrl", "a"]);
    execCommand(editor, "formatFontSize", { size: "36px" });
    expect(getContent(el)).toBe(
        `<p><span style="font-size: 36px;">[abc</span><br><span style="font-size: 36px;"><br>]</span><br></p>`
    );
});
