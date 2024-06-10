import { describe, test } from "@odoo/hoot";
import { testEditor } from "./_helpers/editor";

/**
 * content of the "init" sub suite in editor.test.js
 */

describe("No orphan inline elements compatibility mode", () => {
    test("should wrap inline node inside a p", async () => {
        await testEditor({
            contentBefore: "<p>abc</p> <p>def</p> orphan node",
            contentAfter: '<p>abc</p><p>def</p><p style="margin-bottom: 0px;"> orphan node</p>',
        });
    });

    test("should wrap inline node inside a p (2)", async () => {
        await testEditor({
            contentBefore: "<p>ab</p>cd<p>ef</p>",
            contentAfter: '<p>ab</p><p style="margin-bottom: 0px;">cd</p><p>ef</p>',
        });
    });

    test("should transform root <br> into <p>", async () => {
        await testEditor({
            contentBefore: "ab<br>c",
            contentAfter:
                '<p style="margin-bottom: 0px;">ab</p><p style="margin-bottom: 0px;">c</p>',
        });
    });

    test("should keep <br> if necessary", async () => {
        await testEditor({
            contentBefore: "ab<br><br>c",
            contentAfter:
                '<p style="margin-bottom: 0px;">ab</p><p style="margin-bottom: 0px;"><br></p><p style="margin-bottom: 0px;">c</p>',
        });
    });

    test("should keep multiple conecutive <br> if necessary", async () => {
        await testEditor({
            contentBefore: "ab<br><br><br><br>c",
            contentAfter:
                '<p style="margin-bottom: 0px;">ab</p><p style="margin-bottom: 0px;"><br></p><p style="margin-bottom: 0px;"><br></p><p style="margin-bottom: 0px;"><br></p><p style="margin-bottom: 0px;">c</p>',
        });
    });

    test("should transform complex <br>", async () => {
        await testEditor({
            contentBefore: 'ab<br>c<br>d<span class="keep">xxx</span>e<br>f',
            contentAfter:
                '<p style="margin-bottom: 0px;">ab</p><p style="margin-bottom: 0px;">c</p><p style="margin-bottom: 0px;">d<span class="keep">xxx</span>e</p><p style="margin-bottom: 0px;">f</p>',
        });
    });

    test("should transform complex <br> + keep li ", async () => {
        await testEditor({
            contentBefore: "ab<br>c<ul><li>d</li><li>e</li></ul> f<br>g",
            contentAfter:
                '<p style="margin-bottom: 0px;">ab</p><p style="margin-bottom: 0px;">c</p><ul><li>d</li><li>e</li></ul><p style="margin-bottom: 0px;"> f</p><p style="margin-bottom: 0px;">g</p>',
        });
    });

    test("should not transform <br> inside <p>", async () => {
        await testEditor({
            contentBefore: "<p>ab<br>c</p>",
            contentAfter: "<p>ab<br>c</p>",
        });
        await testEditor({
            contentBefore: "<p>ab<br>c</p><p>d<br></p>",
            contentAfter: "<p>ab<br>c</p><p>d<br></p>",
        });
        await testEditor({
            contentBefore: "xx<p>ab<br>c</p>d<br>yy",
            contentAfter:
                '<p style="margin-bottom: 0px;">xx</p><p>ab<br>c</p><p style="margin-bottom: 0px;">d</p><p style="margin-bottom: 0px;">yy</p>',
        });
    });

    test("should not transform indentation", async () => {
        await testEditor({
            contentBefore: `
<p>ab</p>  
<p>c</p>`,
            contentAfter: `
<p>ab</p>  
<p>c</p>`,
        });
    });

    test("should transform root .fa", async () => {
        await testEditor({
            contentBefore: '<p>ab</p><i class="fa fa-beer"></i><p>c</p>',
            contentAfter:
                '<p>ab</p><p style="margin-bottom: 0px;"><i class="fa fa-beer"></i></p><p>c</p>',
        });
    });

    // This is what the editor currently does (.o_image has display: inline-block)
    // But the resulting editable is NOT valid html (DIV inside P).
    // @todo @phoenix: change behaviour/spec ?
    test("should transform root div.o_image", async () => {
        await testEditor({
            contentBefore: '<p>abc</p><div class="o_image"></div><p>def</p>',
            contentBeforeEdit:
                '<p>abc</p><p style="margin-bottom: 0px;"><div class="o_image" contenteditable="false"></div></p><p>def</p>',
            contentAfter:
                '<p>abc</p><p style="margin-bottom: 0px;"><div class="o_image"></div></p><p>def</p>',
        });
    });
});

describe("allowInlineAtRoot options", () => {
    test("should wrap inline node inside a p by default", async () => {
        await testEditor({
            contentBefore: "abc",
            contentAfter: '<p style="margin-bottom: 0px;">abc</p>',
        });
    });

    test("should wrap inline node inside a p if value is false", async () => {
        await testEditor(
            {
                contentBefore: "abc",
                contentAfter: '<p style="margin-bottom: 0px;">abc</p>',
            },
            { allowInlineAtRoot: false }
        );
    });

    test("should keep inline nodes unchanged if value is true", async () => {
        await testEditor({
            contentBefore: "abc",
            contentAfter: "abc",
            config: { allowInlineAtRoot: true },
        });
    });
});

describe("sanitize spans/fonts", () => {
    test("should NOT sanitize attributeless spans away", async () => {
        await testEditor({
            contentBefore: "<p><span>abc</span></p>",
            contentAfter: "<p><span>abc</span></p>",
        });
    });

    test("should NOT sanitize attributeless fonts away", async () => {
        await testEditor({
            contentBefore: "<p><font>abc</font></p>",
            contentAfter: "<p><font>abc</font></p>",
        });
    });
});

describe("sanitize should modify p within li", () => {
    test("should convert p into span if p has classes", async () => {
        await testEditor({
            contentBefore: '<ul><li><p class="class-1">abc</p><p class="class-2">def</p></li></ul>',
            contentAfter:
                '<ul><li><span class="class-1">abc</span><span class="class-2">def</span></li></ul>',
        });
    });
});
