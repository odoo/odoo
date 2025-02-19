import { describe, expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "../_helpers/editor";
import { getContent } from "../_helpers/selection";
import { click, queryAll, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { execCommand } from "../_helpers/userCommands";
import { expectElementCount } from "../_helpers/ui_expectations";
import { unformat } from "../_helpers/format";

test("should do nothing if no format is set", async () => {
    await testEditor({
        contentBefore: "<div>ab[cd]ef</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test('should not remove "non formating" html class (1)', async () => {
    await testEditor({
        contentBefore: '<div>ab<span class="xyz">[cd]</span>ef</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: '<div>ab<span class="xyz">[cd]</span>ef</div>',
    });
});
test('should not remove "non formating" html class (2)', async () => {
    await testEditor({
        contentBefore: '<div>a[b<span class="xyz">cd</span>e]f</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: '<div>a[b<span class="xyz">cd</span>e]f</div>',
    });
});
test('should not remove "non formating" html class (3)', async () => {
    await testEditor({
        contentBefore: '<div>a<span class="xyz">b[cd]e</span>f</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: '<div>a<span class="xyz">b[cd]e</span>f</div>',
    });
});
test("should remove bold format (1)", async () => {
    await testEditor({
        contentBefore: "<div>ab<b>[cd]</b>ef</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove bold format (2)", async () => {
    await testEditor({
        contentBefore: "<div>ab[<b>cd]</b>ef</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove bold format (3)", async () => {
    await testEditor({
        contentBefore: "<div>ab<b>[cd</b>]ef</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove bold format (4)", async () => {
    await testEditor({
        contentBefore: "<div>ab[<b>cd</b>]ef</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove bold format (5)", async () => {
    await testEditor({
        contentBefore: "<div>ab[<b>cd</b>]ef</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove bold format (6)", async () => {
    await testEditor({
        contentBefore: "<div>a<b>b[cd]e</b>f</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>a<b>b</b>[cd]<b>e</b>f</div>",
    });
});
test("should remove bold format (7)", async () => {
    await testEditor({
        contentBefore: "<div>a<b>b[c</b>d]ef</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>a<b>b</b>[cd]ef</div>",
    });
});
test("should remove bold format (8)", async () => {
    await testEditor({
        contentBefore: '<div>ab<font style="font-weight: bold">[cd]</font>ef</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove bold format (9)", async () => {
    await testEditor({
        contentBefore: '<div>ab<font style="font-weight: bolder">[cd]</font>ef</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove bold format (10)", async () => {
    await testEditor({
        contentBefore: '<div>ab<font style="font-weight: 500">[cd]</font>ef</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove bold format (11)", async () => {
    await testEditor({
        contentBefore: '<div>ab<font style="font-weight: 600">[cd]</font>ef</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove bold format (12)", async () => {
    await testEditor({
        contentBefore: '<div>a<font style="font-weight: 600">b[cd]e</font>f</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter:
            '<div>a<font style="font-weight: 600">b</font>[cd]<font style="font-weight: 600">e</font>f</div>',
    });
});
test("should remove bold format (13)", async () => {
    await testEditor({
        contentBefore: "<div>ab<strong>[cd]</strong>ef</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove bold format (14)", async () => {
    await testEditor({
        contentBefore: "<div>a<strong>b[cd]e</strong>f</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>a<strong>b</strong>[cd]<strong>e</strong>f</div>",
    });
});
test("should remove italic format (1)", async () => {
    await testEditor({
        contentBefore: "<div>ab<i>[cd]</i>ef</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove italic format (2)", async () => {
    await testEditor({
        contentBefore: "<div>ab[<i>cd]</i>ef</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove italic format (3)", async () => {
    await testEditor({
        contentBefore: "<div>ab<i>[cd</i>]ef</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove italic format (4)", async () => {
    await testEditor({
        contentBefore: "<div>ab[<i>cd</i>]ef</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove italic format (5)", async () => {
    await testEditor({
        contentBefore: "<div>ab[<i>cd</i>]ef</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove italic format (6)", async () => {
    await testEditor({
        contentBefore: "<div>a<i>b[cd]e</i>f</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>a<i>b</i>[cd]<i>e</i>f</div>",
    });
});
test("should remove italic format (7)", async () => {
    await testEditor({
        contentBefore: "<div>a<i>b[c</i>d]ef</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>a<i>b</i>[cd]ef</div>",
    });
});
test("should remove italic format (8)", async () => {
    await testEditor({
        contentBefore: '<div>ab<font style="font-style: italic">[cd]</font>ef</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove italic format (9)", async () => {
    await testEditor({
        contentBefore: '<div>a<font style="font-style: italic">b[cd]e</font>f</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter:
            '<div>a<font style="font-style: italic">b</font>[cd]<font style="font-style: italic">e</font>f</div>',
    });
});
test("should remove underline format (1)", async () => {
    await testEditor({
        contentBefore: "<div>ab<u>[cd]</u>ef</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove underline format (2)", async () => {
    await testEditor({
        contentBefore: "<div>ab[<u>cd]</u>ef</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove underline format (3)", async () => {
    await testEditor({
        contentBefore: "<div>ab<u>[cd</u>]ef</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove underline format (4)", async () => {
    await testEditor({
        contentBefore: "<div>ab[<u>cd</u>]ef</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove underline format (5)", async () => {
    await testEditor({
        contentBefore: "<div>ab[<u>cd</u>]ef</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove underline format (6)", async () => {
    await testEditor({
        contentBefore: "<div>a<u>b[cd]e</u>f</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>a<u>b</u>[cd]<u>e</u>f</div>",
    });
});
test("should remove underline format (7)", async () => {
    await testEditor({
        contentBefore: "<div>a<u>b[c</u>d]ef</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>a<u>b</u>[cd]ef</div>",
    });
});
test("should remove underline format (8)", async () => {
    await testEditor({
        contentBefore: '<div>ab<font style="text-decoration: underline">[cd]</font>ef</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove underline format (9)", async () => {
    await testEditor({
        contentBefore: '<div>a<font style="text-decoration: underline">b[cd]e</font>f</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter:
            '<div>a<font style="text-decoration: underline">b</font>[cd]<font style="text-decoration: underline">e</font>f</div>',
    });
});
test("should remove underline format (10)", async () => {
    await testEditor({
        contentBefore: '<div>a<font style="text-decoration-line: underline">b[cd]e</font>f</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter:
            '<div>a<font style="text-decoration-line: underline">b</font>[cd]<font style="text-decoration-line: underline">e</font>f</div>',
    });
});
test("should remove striketrough format (1)", async () => {
    await testEditor({
        contentBefore: "<div>ab<s>[cd]</s>ef</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove striketrough format (2)", async () => {
    await testEditor({
        contentBefore: "<div>ab[<s>cd]</s>ef</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove striketrough format (3)", async () => {
    await testEditor({
        contentBefore: "<div>ab<s>[cd</s>]ef</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove striketrough format (4)", async () => {
    await testEditor({
        contentBefore: "<div>ab[<s>cd</s>]ef</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove striketrough format (5)", async () => {
    await testEditor({
        contentBefore: "<div>ab[<s>cd</s>]ef</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove striketrough format (6)", async () => {
    await testEditor({
        contentBefore: "<div>a<s>b[cd]e</s>f</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>a<s>b</s>[cd]<s>e</s>f</div>",
    });
});
test("should remove striketrough format (7)", async () => {
    await testEditor({
        contentBefore: "<div>a<s>b[c</s>d]ef</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>a<s>b</s>[cd]ef</div>",
    });
});
test("should remove striketrough format (8)", async () => {
    await testEditor({
        contentBefore: '<div>ab<font style="text-decoration: line-through">[cd]</font>ef</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove striketrough format (9)", async () => {
    await testEditor({
        contentBefore: '<div>a<font style="text-decoration: line-through">b[cd]e</font>f</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter:
            '<div>a<font style="text-decoration: line-through">b</font>[cd]<font style="text-decoration: line-through">e</font>f</div>',
    });
});
test("should remove striketrough format (10)", async () => {
    await testEditor({
        contentBefore:
            '<div>a<font style="text-decoration-line: line-through">b[cd]e</font>f</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter:
            '<div>a<font style="text-decoration-line: line-through">b</font>[cd]<font style="text-decoration-line: line-through">e</font>f</div>',
    });
});
test("should remove text color (1)", async () => {
    await testEditor({
        contentBefore: '<div>ab<font style="color: rgb(255, 0, 0);">[cd]</font>ef</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove text color (2)", async () => {
    await testEditor({
        contentBefore: '<div>ab<font style="color: red">[cd]</font>ef</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove text color (3)", async () => {
    await testEditor({
        contentBefore: '<div>ab<font style="color: #ff0000">[cd]</font>ef</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove text color (4)", async () => {
    await testEditor({
        contentBefore: '<div>ab<font class="text-o-color-1">[cd]</font>ef</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove text color (5)", async () => {
    await testEditor({
        contentBefore: '<div>a<font style="color: rgb(255, 0, 0);">b[cd]e</font>f</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter:
            '<div>a<font style="color: rgb(255, 0, 0);">b</font>[cd]<font style="color: rgb(255, 0, 0);">e</font>f</div>',
    });
});
test("should remove text color (6)", async () => {
    await testEditor({
        contentBefore: '<div>a<font style="color: red">b[cd]e</font>f</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter:
            '<div>a<font style="color: red">b</font>[cd]<font style="color: red">e</font>f</div>',
    });
});
test("should remove text color (7)", async () => {
    await testEditor({
        contentBefore: '<div>a<font style="color: #ff0000">b[cd]e</font>f</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter:
            '<div>a<font style="color: #ff0000">b</font>[cd]<font style="color: #ff0000">e</font>f</div>',
    });
});
test("should remove text color (8)", async () => {
    await testEditor({
        contentBefore: '<div>a<font class="text-o-color-1">b[cd]e</font>f</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter:
            '<div>a<font class="text-o-color-1">b</font>[cd]<font class="text-o-color-1">e</font>f</div>',
    });
});
test("should remove background color (1)", async () => {
    await testEditor({
        contentBefore: '<div>ab<font style="background: rgb(0, 0, 255);">[cd]</font>ef</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove background color (2)", async () => {
    await testEditor({
        contentBefore: '<div>ab<font style="background: blue">[cd]</font>ef</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove background color (3)", async () => {
    await testEditor({
        contentBefore: '<div>ab<font style="background: #00f">[cd]</font>ef</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove background color (4)", async () => {
    await testEditor({
        contentBefore: '<div>ab<font style="background-color: #00f">[cd]</font>ef</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove background color (5)", async () => {
    await testEditor({
        contentBefore: '<div>ab<font class="bg-o-color-1">[cd]</font>ef</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove background color (6)", async () => {
    await testEditor({
        contentBefore: '<div>a<font style="background: rgb(255, 0, 0);">b[cd]e</font>f</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter:
            '<div>a<font style="background: rgb(255, 0, 0);">b</font>[cd]<font style="background: rgb(255, 0, 0);">e</font>f</div>',
    });
});
test("should remove background color (7)", async () => {
    await testEditor({
        contentBefore: '<div>a<font style="background: red">b[cd]e</font>f</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter:
            '<div>a<font style="background: red">b</font>[cd]<font style="background: red">e</font>f</div>',
    });
});
test("should remove background color (8)", async () => {
    await testEditor({
        contentBefore: '<div>a<font style="background: #ff0000">b[cd]e</font>f</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter:
            '<div>a<font style="background: #ff0000">b</font>[cd]<font style="background: #ff0000">e</font>f</div>',
    });
});
test("should remove background color (9)", async () => {
    await testEditor({
        contentBefore: '<div>a<font style="background-color: #ff0000">b[cd]e</font>f</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter:
            '<div>a<font style="background-color: #ff0000">b</font>[cd]<font style="background-color: #ff0000">e</font>f</div>',
    });
});
test("should remove background color (10)", async () => {
    await testEditor({
        contentBefore: '<div>a<font class="bg-o-color-1">b[cd]e</font>f</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter:
            '<div>a<font class="bg-o-color-1">b</font>[cd]<font class="bg-o-color-1">e</font>f</div>',
    });
});
test("should remove the background image when clear the format", async () => {
    await testEditor({
        contentBefore:
            '<div><p><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(255, 204, 51) 0%, rgb(226, 51, 255) 100%);">[ab]</font></p></div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div><p>[ab]</p></div>",
    });
});
test("should remove all the colors for the text separated by Shift+Enter when using removeFormat button (1)", async () => {
    await testEditor({
        contentBefore: `<div><h1><font style="color: red">[ab</font><br><font style="color: red">cd</font><br><font style="color: red">ef]</font></h1></div>`,
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: `<div><h1>[ab<br>cd<br>ef]</h1></div>`,
    });
});
test("should remove all the colors for the text separated by Shift+Enter when using removeFormat button (2)", async () => {
    await testEditor({
        contentBefore: `<div><h1><font style="color: red">[ab</font><br><font style="color: red">cd</font><br><font style="color: red">]ef</font></h1></div>`,
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: `<div><h1>[ab<br>cd<br><font style="color: red">]ef</font></h1></div>`,
    });
});
test("should remove all the colors for the text separated by Enter when using removeFormat button", async () => {
    await testEditor({
        contentBefore: `<div><h1><font style="background-color: red">[ab</font></h1><h1><font style="background-color: red">cd</font></h1><h1><font style="background-color: red">ef]</font></h1></div>`,
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: `<div><h1>[ab</h1><h1>cd</h1><h1>ef]</h1></div>`,
    });
    await testEditor({
        contentBefore: `<div><h1><font style="color: red">[ab</font></h1><h1><font style="color: red">cd</font></h1><h1><font style="color: red">ef]</font></h1></div>`,
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: `<div><h1>[ab</h1><h1>cd</h1><h1>ef]</h1></div>`,
    });
});
test("should remove multiple format (1)", async () => {
    await testEditor({
        contentBefore: "<div>ab<b>[cd</b>ef<i>gh]</i>ij</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cdefgh]ij</div>",
    });
});
test("should remove multiple format (2)", async () => {
    await testEditor({
        contentBefore: "<div>ab<b>[c<u>d</u></b>ef<i>g</i>h]ij</div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cdefgh]ij</div>",
    });
});
test("should remove multiple format (3)", async () => {
    await testEditor({
        contentBefore: "<div><p><b>a[bc</b></p><p>de<br>fg<br></p><p><i>ij</i>sd]fsf</p></div>",
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div><p><b>a</b>[bc</p><p>de<br>fg<br></p><p>ijsd]fsf</p></div>",
    });
});
test("should remove format and keep attribute in a span", async () => {
    await testEditor({
        contentBefore: '<p><strong some-attr="1">[abc]</strong></p>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: '<p><span some-attr="1">[abc]</span></p>',
    });
});
test("should remove multiple color (1)", async () => {
    await testEditor({
        contentBefore:
            '<div>ab<font style="background: rgb(0, 0, 255);color: rgb(0, 255, 255);">[cd]</font>ef</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove multiple color (2)", async () => {
    await testEditor({
        contentBefore:
            '<div>ab<font style="background: red" class="bg-o-color-1">[cd]</font>ef</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove multiple color (3)", async () => {
    await testEditor({
        contentBefore:
            '<div>ab<font style="background: rgb(0, 0, 255);"><font class="bg-o-color-1">[cd]</font></font>ef</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove multiple color (4)", async () => {
    await testEditor({
        contentBefore:
            '<div>ab<font style="color: rgb(0, 0, 255);"><font class="bg-o-color-1">[cd]</font></font>ef</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div>ab[cd]ef</div>",
    });
});
test("should remove multiple color (5)", async () => {
    await testEditor({
        contentBefore:
            '<div>ab<font style="background: blue">c[d<font class="bg-o-color-1">ef]</font></font>gh</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: '<div>ab<font style="background: blue">c</font>[def]gh</div>',
    });
});
// TODO: we should avoid <font> element into <font> element when possible
test.todo("should remove multiple color (6)", async () => {
    await testEditor({
        contentBefore:
            '<div>ab<font style="background: blue">c[d<font class="bg-o-color-1">e]f</font></font>gh</div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter:
            '<div>ab<font style="background: blue">c</font>[de]<font class="bg-o-color-1">f</font>gh</div>',
    });
});
test("undo remove format should return the element to it's original state", async () => {
    await testEditor({
        contentBefore:
            '<p><strong><em><u><s><font style="color: rgb(0, 255, 0); background: rgb(0, 0, 255);">[sdsdsdsds]</font></s></u></em></strong></p>',
        stepFunction: (editor) => {
            execCommand(editor, "removeFormat");
            execCommand(editor, "historyUndo");
        },
        contentAfter:
            '<p><strong><em><u><s><font style="color: rgb(0, 255, 0); background: rgb(0, 0, 255);">[sdsdsdsds]</font></s></u></em></strong></p>',
    });
});

test("should remove font size class from selected text", async () => {
    await testEditor({
        contentBefore: '<p>a<span class="h1-fs">[bcd]</span>e</p>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<p>a[bcd]e</p>",
    });
});

test("should remove font size classes from multiple sized selected text", async () => {
    await testEditor({
        contentBefore:
            '<p>a<span class="h1-fs">[hello </span><span class="h2-fs">world]</span>b</p>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<p>a[hello world]b</p>",
    });
});

test("should remove font size class from multiple formatted selected text", async () => {
    await testEditor({
        contentBefore: '<p>a<strong>bc<span class="h2-fs">[de]</span>fg</strong>h</p>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<p>a<strong>bc</strong>[de]<strong>fg</strong>h</p>",
    });
});

test("should remove font-size style from selected text", async () => {
    await testEditor({
        contentBefore: `<p>ab<span style="font-size: 10px;">[cde]</span>fg</p>`,
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<p>ab[cde]fg</p>",
    });
});

test("should remove font-size style from multiple formatted selected text", async () => {
    await testEditor({
        contentBefore: '<p>a<strong>bc<span style="font-size: 10px;">[de]</span>fg</strong>h</p>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<p>a<strong>bc</strong>[de]<strong>fg</strong>h</p>",
    });
});

test("should remove font-size style from multiple sized selected text", async () => {
    await testEditor({
        contentBefore:
            '<p>a<span style="font-size: 10px;">[hello </span><span style="font-size: 10px;">world]</span>b</p>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<p>a[hello world]b</p>",
    });
});

test("should remove font size and color styles", async () => {
    await testEditor({
        contentBefore: `<p><span class="display-1-fs"><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">[abcdefg]</font></span></p>`,
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: `<p>[abcdefg]</p>`,
    });
    await testEditor({
        contentBefore: `<p><span style="font-size: 10px;"><font style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">[abcdefg]</font></span></p>`,
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: `<p>[abcdefg]</p>`,
    });
});

test("should remove backgroundColor from selected cells using removeFormat", async () => {
    const defaultTextColor = "color: rgb(1, 10, 100);";
    const styleContent = `* {${defaultTextColor}}`;
    await testEditor({
        contentBefore: unformat(`
            <table class="table table-bordered o_table"><tbody>
                <tr><td style="background-color: rgb(255, 0, 0); ${defaultTextColor}"><p>[ab</p></td></tr>
                <tr><td style="background-color: rgb(255, 0, 0); ${defaultTextColor}"><p>cd]</p></td></tr>
            </tbody></table>
        `),
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: unformat(`
            <table class="table table-bordered o_table"><tbody>
                <tr><td><p>[ab</p></td></tr>
                <tr><td><p>cd]</p></td></tr>
            </tbody></table>
        `),
        styleContent,
    });
});

test("should remove backgroundColor from selected cells using removeFormat (2)", async () => {
    const defaultTextColor = "color: rgb(1, 10, 100);";
    const styleContent = `* {${defaultTextColor}}`;
    await testEditor({
        contentBefore: unformat(`
            <table class="table table-bordered o_table"><tbody>
                <tr><td style="background-color: rgb(255, 0, 0); ${defaultTextColor}"><p>[<br></p></td></tr>
                <tr><td style="background-color: rgb(255, 0, 0); ${defaultTextColor}"><p>]<br></p></td></tr>
            </tbody></table>
        `),
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: unformat(`
            <table class="table table-bordered o_table"><tbody>
                <tr><td><p>[\u200b</p></td></tr>
                <tr><td><p>]\u200b</p></td></tr>
            </tbody></table>
        `),
        styleContent,
    });
});

test("should remove all formats when having multiple formats", async () => {
    await testEditor({
        contentBefore:
            '<p><span class="display-4-fs"><font style="color: rgb(255, 156, 0);"><strong>[test]</strong></font></span></p>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<p>[test]</p>",
    });
});

test("should remove all formats when having multiple formats (2)", async () => {
    await testEditor({
        contentBefore:
            '<p><span style="font-size: 24px"><font style="color: rgb(255, 156, 0);"><strong>[test]</strong></font></span></p>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<p>[test]</p>",
    });
});

test("should remove all formats when having multiple formats (3)", async () => {
    await testEditor({
        contentBefore:
            '<p><span class="display-4-fs"><font class="text-o-color-1"><strong>[test]</strong></font></span></p>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<p>[test]</p>",
    });
});

test("should remove color from entire heading when fully selected", async () => {
    await testEditor({
        contentBefore: '<div><h1 style="color: rgb(255, 0, 0);">[abcd]</h1></div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<div><h1>[abcd]</h1></div>",
    });
});

test("should remove color only from selected text within a heading", async () => {
    await testEditor({
        contentBefore: '<div><h1 style="color: rgb(255, 0, 0);">a[bc]d</h1></div>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter:
            '<div><h1><font style="color: rgb(255, 0, 0);">a</font>[bc]<font style="color: rgb(255, 0, 0);">d</font></h1></div>',
    });
});

test("should remove gradient color from span element", async () => {
    await testEditor({
        contentBefore:
            '<p><span style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">[ab]</span></p>',
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: "<p>[ab]</p>",
    });
});

describe("Toolbar", () => {
    async function removeFormatClick() {
        await expectElementCount(".o-we-toolbar", 1);
        expect(".btn[name='remove_format']").toHaveCount(1); // remove format
        expect(".btn[name='remove_format']").not.toHaveClass("disabled"); // remove format button should not be disabled

        await click(".btn[name='remove_format']");
        await animationFrame();
        await expectElementCount(".o-we-toolbar", 1);
        expect(".btn[name='remove_format']").toHaveClass("disabled"); // remove format button should be disabled
    }

    test("Should remove bold from selection", async () => {
        const { el } = await setupEditor(`<p>this <b>is[ a ]UX</b> test.</p>`);
        await removeFormatClick();
        expect(getContent(el)).toBe(`<p>this <b>is</b>[ a ]<b>UX</b> test.</p>`);
    });

    test("Should remove color from selection", async () => {
        const { el } = await setupEditor(
            `<p>this <span style="color:red">is[ a ]UX</span> test.</p>`
        );
        await removeFormatClick();
        expect(getContent(el)).toBe(
            `<p>this <span style="color:red">is</span>[ a ]<span style="color:red">UX</span> test.</p>`
        );
        await click(".btn .fa-eraser");
        expect(getContent(el)).toBe(
            `<p>this <span style="color:red">is</span>[ a ]<span style="color:red">UX</span> test.</p>`
        );
    });

    test("Should remove background color from selection", async () => {
        const { el } = await setupEditor(
            `<p>this <span style="background:green">is[ a ]UX</span> test.</p>`
        );
        await removeFormatClick();
        expect(getContent(el)).toBe(
            `<p>this <span style="background:green">is</span>[ a ]<span style="background:green">UX</span> test.</p>`
        );
    });

    test("Should remove background class color from selection", async () => {
        const { el } = await setupEditor(
            `<p>this <font class="text-o-color-1">is[ a ]UX</font> test.</p>`
        );
        await removeFormatClick();
        expect(getContent(el)).toBe(
            `<p>this <font class="text-o-color-1">is</font>[ a ]<font class="text-o-color-1">UX</font> test.</p>`
        );
    });

    test("Should do nothing when no format in selection", async () => {
        const { el } = await setupEditor(
            `<p>this <span class="random-class">is[ a ]UX</span> test.</p>`
        );
        await expectElementCount(".o-we-toolbar", 1);
        expect(".btn[name='remove_format']").toHaveCount(1); // remove format
        expect(".btn[name='remove_format']").toHaveClass("disabled"); // remove format button should be disabled when no format

        await click(".btn[name='remove_format']");
        await animationFrame();
        await expectElementCount(".o-we-toolbar", 1);
        expect(".btn[name='remove_format']").toHaveClass("disabled"); // remove format button should still be disabled
        expect(getContent(el)).toBe(
            `<p>this <span class="random-class">is[ a ]UX</span> test.</p>`
        );
    });

    test("Remove format button should be available if selection contains formatted nodes among unformatted nodes", async () => {
        const { el } = await setupEditor(`<p>this <b>is[ a UX</b> te]st.</p>`);
        await expectElementCount(".o-we-toolbar", 1);
        expect(".btn[name='remove_format']").toHaveCount(1); // remove format
        expect(".btn[name='remove_format']").not.toHaveClass("disabled"); // remove format button should not be disabled

        await click(".btn[name='remove_format']");
        await animationFrame();
        await expectElementCount(".o-we-toolbar", 1);
        expect(".btn[name='remove_format']").toHaveClass("disabled"); // remove format button should now be disabled
        expect(getContent(el)).toBe(`<p>this <b>is</b>[ a UX te]st.</p>`);
    });

    test("Remove format button should be the last one in the decoration button group", async () => {
        await setupEditor("<p>[abc]</p>");
        await waitFor(".o-we-toolbar");
        const formatButtons = queryAll(".o-we-toolbar .btn-group[name='decoration'] .btn");
        expect(formatButtons.at(-1)).toHaveAttribute("name", "remove_format");
    });

    test("Remove format button should be enabled when font-sized text is selected", async () => {
        await setupEditor('<p><span class="h1-fs">[abc]</span></p>');
        await waitFor(".o-we-toolbar");
        expect(".btn[name='remove_format']").toHaveCount(1);
        expect(".btn[name='remove_format'].disabled").toHaveCount(0);
    });

    test("Should remove background color of text within a fully selected table", async () => {
        const { el } = await setupEditor(
            `<table class="table table-bordered o_table o_selected_table"><tbody><tr><td class="o_selected_td"><p><font style="background-color: rgb(255, 0, 0);">[abc</font></p></td><td class="o_selected_td"><p><br></p></td></tr></tbody></table><p>]<br></p>`
        );
        await removeFormatClick();
        expect(getContent(el)).toBe(
            `<table class="table table-bordered o_table o_selected_table"><tbody><tr><td class="o_selected_td"><p>[abc</p></td><td class="o_selected_td"><p>\u200b</p></td></tr></tbody></table><p>]\u200b</p>`
        );
    });

    test("Should remove background color of a table cell", async () => {
        const { el } = await setupEditor(
            `<table class="table table-bordered o_table o_selected_table"><tbody><tr><td style="background-color: rgb(255, 0, 0);" class="o_selected_td"><p>[<br></p></td><td style="background-color: rgb(255, 0, 0);" class="o_selected_td"><p>]<br></p></td></tr></tbody></table>`
        );
        await removeFormatClick();
        expect(getContent(el)).toBe(
            `<table class="table table-bordered o_table o_selected_table"><tbody><tr><td style="" class="o_selected_td"><p>[\u200b</p></td><td style="" class="o_selected_td"><p>]\u200b</p></td></tr></tbody></table>`
        );
    });
});
