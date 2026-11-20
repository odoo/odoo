import { describe, expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "./_helpers/editor";
import { unformat } from "./_helpers/format";
import { FORMATTABLE_TAGS } from "@html_editor/utils/formatting";
import { QWebPlugin } from "@html_editor/others/qweb_plugin";

/**
 * content of the "init" sub suite in editor.test.js
 */

describe("No orphan inline elements compatibility mode", () => {
    test("should wrap inline node inside a div baseContainer", async () => {
        await testEditor({
            contentBefore: "<p>abc</p> <p>def</p> orphan node",
            contentAfter: "<p>abc</p><p>def</p><div> orphan node</div>",
        });
    });

    test("should wrap inline node inside a div baseContainer (2)", async () => {
        await testEditor({
            contentBefore: "<p>ab</p>cd<p>ef</p>",
            contentAfter: "<p>ab</p><div>cd</div><p>ef</p>",
        });
    });

    test("should transform root <br> into a div baseContainer", async () => {
        await testEditor({
            contentBefore: "ab<br>c",
            contentAfter: "<div>ab</div><div>c</div>",
        });
    });

    test("should keep <br> if necessary", async () => {
        await testEditor({
            contentBefore: "ab<br><br>c",
            contentAfter: "<div>ab</div><div><br></div><div>c</div>",
        });
    });

    test("should keep multiple conecutive <br> if necessary", async () => {
        await testEditor({
            contentBefore: "ab<br><br><br><br>c",
            contentAfter: "<div>ab</div><div><br></div><div><br></div><div><br></div><div>c</div>",
        });
    });

    test("should transform complex <br>", async () => {
        await testEditor({
            contentBefore: 'ab<br>c<br>d<span class="keep">xxx</span>e<br>f',
            contentAfter:
                '<div>ab</div><div>c</div><div>d<span class="keep">xxx</span>e</div><div>f</div>',
        });
    });

    test("should transform complex <br> + keep li ", async () => {
        await testEditor({
            contentBefore: "ab<br>c<ul><li>d</li><li>e</li></ul> f<br>g",
            contentAfter:
                "<div>ab</div><div>c</div><ul><li>d</li><li>e</li></ul><div> f</div><div>g</div>",
        });
    });

    test("should not transform <br> inside <p> (1)", async () => {
        await testEditor({
            contentBefore: "<p>ab<br>c</p>",
            contentAfter: "<p>ab<br>c</p>",
        });
    });

    test("should not transform <br> inside <p> (2)", async () => {
        await testEditor({
            contentBefore: "<p>ab<br>c</p><p>d<br></p>",
            contentAfter: "<p>ab<br>c</p><p>d<br></p>",
        });
    });

    test("should not transform <br> inside <p> (3)", async () => {
        await testEditor({
            contentBefore: "xx<p>ab<br>c</p>d<br>yy",
            contentAfter: "<div>xx</div><p>ab<br>c</p><div>d</div><div>yy</div>",
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

    test("should transform root .oi", async () => {
        await testEditor({
            contentBefore: '<p>ab</p><i class="oi" data-icon="sports_bar"></i><p>c</p>',
            contentAfter: '<p>ab</p><div><i class="oi" data-icon="sports_bar"></i></div><p>c</p>',
        });
    });

    test("should wrap a div.o_file_box direct child of the editable into a block", async () => {
        await testEditor({
            contentBefore:
                '<p>abc</p><span class="o_file_box" contenteditable="false"><a href="#" title="document" data-mimetype="application/pdf"></a></span><p>def</p>',
            contentBeforeEdit:
                '<p>abc</p><div class="o-paragraph">\ufeff<span class="o_file_box" contenteditable="false"><a href="#" title="document" data-mimetype="application/pdf"></a></span>\ufeff</div><p>def</p>',
            contentAfter:
                '<p>abc</p><div><span class="o_file_box"><a href="#" title="document" data-mimetype="application/pdf"></a></span></div><p>def</p>',
        });
    });
});

describe("allowInlineAtRoot options", () => {
    test("should wrap inline node inside a p by default", async () => {
        await testEditor({
            contentBefore: "abc",
            contentAfter: "<div>abc</div>",
        });
    });

    test("should wrap inline node inside a p if value is false", async () => {
        await testEditor(
            {
                contentBefore: "abc",
                contentAfter: "<div>abc</div>",
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

describe("list normalization", () => {
    test("should keep P in LI (regardless of class)", async () => {
        await testEditor({
            contentBefore: '<ul><li><p class="class-1">abc</p><p>def</p></li></ul>',
            contentAfter: '<ul><li><p class="class-1">abc</p><p>def</p></li></ul>',
        });
    });
    test("should keep inlines in LI", async () => {
        await testEditor({
            contentBefore: "<ul><li>abc<strong>def</strong></li></ul>",
            contentAfter: "<ul><li>abc<strong>def</strong></li></ul>",
        });
    });
    test("should wrap inlines in P to prevent mixing block and inline in LI", async () => {
        await testEditor({
            contentBefore: "<ul><li>abc<strong>def</strong><p>ghi</p></li></ul>",
            contentAfter: "<ul><li><p>abc<strong>def</strong></p><p>ghi</p></li></ul>",
        });
    });
});

describe("link normalization", () => {
    test("should move inline color from anchor to font", async () => {
        await testEditor({
            contentBefore: '<p><a href="#" style="color: #008f8c">test</a></p>',
            contentAfter:
                '<p><a href="#"><font style="color: rgb(0, 143, 140);">test</font></a></p>',
        });
    });

    test("should remove anchor color and retain font color", async () => {
        await testEditor({
            contentBefore:
                '<p><a href="#" style="color: #008f8c"><font style="color: rgb(255, 0, 0);">test</font></a></p>',
            contentAfter: '<p><a href="#"><font style="color: rgb(255, 0, 0);">test</font></a></p>',
        });
    });

    test("should handle inline color styles in multiple anchor elements", async () => {
        await testEditor({
            contentBefore:
                '<p><a href="#" style="color: #008f8c"><font style="color: rgb(255, 0, 0);">test</font></a></p><p><a href="#" style="color: #008f8c">test</a></p>',
            contentAfter:
                '<p><a href="#"><font style="color: rgb(255, 0, 0);">test</font></a></p><p><a href="#"><font style="color: rgb(0, 143, 140);">test</font></a></p>',
        });
    });
});

describe("color normalization", () => {
    test("should unwrap nested identical <font> tags with gradient (class and style same)", async () => {
        await testEditor({
            contentBefore: unformat(`
                <p><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">
                    parent
                    <font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">child</font>
                </font></p>
            `),
            contentAfter: unformat(`
                <p><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">parentchild</font></p>
            `),
        });
    });

    test("should unwrap nested identical <font> tag when parent already has the same class", async () => {
        await testEditor({
            contentBefore: unformat(`
                <p><font class="bg-color-1 text-gradient" style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">
                    parent
                    <font class="bg-color-1">child</font>
                </font></p>
            `),
            contentAfter: unformat(`
                <p><font class="bg-color-1 text-gradient" style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">parentchild</font></p>
            `),
        });
    });

    test("should unwrap nested identical <font> tags with color (class and style same)", async () => {
        await testEditor({
            contentBefore: unformat(`
                <p><font class="bg-color-1" style="color:red">
                    parent
                    <font class="bg-color-1" style="color:red">child</font>
                </font></p>
            `),
            contentAfter: unformat(`
                <p><font class="bg-color-1" style="color:red">parentchild</font></p>
            `),
        });
    });

    test("should unwrap nested <font> with same style but no class", async () => {
        await testEditor({
            contentBefore: unformat(`
                <p><font class="bg-color-1" style="color:red">
                    parent
                    <font style="color:red">child</font>
                </font></p>
            `),
            contentAfter: unformat(`
                <p><font class="bg-color-1" style="color:red">parentchild</font></p>
            `),
        });
    });

    test("should unwrap nested <font> with same class only", async () => {
        await testEditor({
            contentBefore: unformat(`
                <p><font class="bg-color-1" style="color:red">
                    parent
                    <font class="bg-color-1">child</font>
                </font></p>
            `),
            contentAfter: unformat(`
                <p><font class="bg-color-1" style="color:red">parentchild</font></p>
            `),
        });
    });

    test("should unwrap nested <font> with no class or style", async () => {
        await testEditor({
            contentBefore: unformat(`
                <p><font class="bg-color-1" style="color:red">
                    parent
                    <font>child</font>
                </font></p>
            `),
            contentAfter: unformat(`
                <p><font class="bg-color-1" style="color:red">parentchild</font></p>
            `),
        });
    });

    test("should unwrap nested <font> with same style and class as closest <font>", async () => {
        await testEditor({
            contentBefore: unformat(`
                <p><font class="bg-color-1" style="color:red">
                        parent
                        <strong>
                            text1
                            <font class="bg-color-1" style="color:red">child</font>
                            text2
                        </strong>
                </font></p>
            `),
            contentAfter: unformat(`
                <p><font class="bg-color-1" style="color:red">
                        parent<strong>text1childtext2</strong>
                </font></p>
            `),
        });
    });

    test("should unwrap nested identical <font> tags inside a QWeb directive", async () => {
        await testEditor({
            config: { includePlugins: [QWebPlugin] },
            contentBefore: `<p><font style="color: red;">a<t t-if="test"><font style="color: red;">b</font></t></font></p>`,
            contentAfter: `<p><font style="color: red;">a<t t-if="test">b</t></font></p>`,
        });
    });
});

describe("formatting normalization", () => {
    test("should unwrap nested identical bold tags (1)", async () => {
        await testEditor({
            contentBefore: "<p>a<strong>b<strong>c<strong>d</strong></strong>e</strong>f</p>",
            contentAfter: "<p>a<strong>bcde</strong>f</p>",
        });
    });

    test("should unwrap nested identical bold tags (2)", async () => {
        await testEditor({
            contentBefore: `<p>a<span style="font-weight: bolder;">b<span style="font-weight: bolder;">c<span style="font-weight: bolder;">d</span></span>e</span>f</p>`,
            contentAfter: `<p>a<span style="font-weight: bolder;">bcde</span>f</p>`,
        });
    });

    test("should unwrap nested identical bold tags (3)", async () => {
        await testEditor({
            contentBefore: "<p>a<b>b<b>c<b>d</b></b>e</b>f</p>",
            contentAfter: "<p>a<b>bcde</b>f</p>",
        });
    });

    test("should merge nested strong inside formatting tags", async () => {
        await testEditor({
            contentBefore: unformat(`
                <p>
                    <strong>
                        <em>
                            <u>
                                <s>
                                    text1
                                    <strong>text2</strong>
                                    text3
                                </s>
                            </u>
                        </em>
                    </strong>
                </p>
            `),
            contentAfter: unformat(`
                <p>
                    <strong>
                        <em>
                            <u>
                                <s>
                                    text1text2text3
                                </s>
                            </u>
                        </em>
                    </strong>
                </p>
            `),
        });
    });

    test("should merge nested small inside formatting tags", async () => {
        await testEditor({
            contentBefore: `<p><small><small>text</small></small></p>`,
            contentAfter: `<p><small>text</small></p>`,
        });
    });

    for (const tagName of FORMATTABLE_TAGS.map((tag) => tag.toLowerCase())) {
        test(`merges adjacent formattable ${tagName}`, async () => {
            await testEditor({
                contentBefore: `<p><${tagName}>A</${tagName}><${tagName}>B</${tagName}></p>`,
                contentAfter: `<p><${tagName}>AB</${tagName}></p>`,
            });
        });
    }

    test("should not unwrap font-weight: normal inside a bold parent", async () => {
        await testEditor({
            styleContent: `.boldClass { font-weight: bold; }`,
            contentBefore: `<p class="boldClass">a<font style="font-weight: normal;">b</font>c</p>`,
            contentAfter: `<p class="boldClass">a<font style="font-weight: normal;">b</font>c</p>`,
        });
    });

    test("should unwrap nested bold tags inside a QWeb directive", async () => {
        await testEditor({
            config: { includePlugins: [QWebPlugin] },
            contentBefore: `<p><strong>a<t t-if="test"><strong>b</strong></t></strong></p>`,
            contentAfter: `<p><strong>a<t t-if="test">b</t></strong></p>`,
        });
    });

    test("should not unwrap intermediate color style override", async () => {
        await testEditor({
            contentBefore: `<p><font style="color: red;"><span style="color: blue;"><font style="color: red;">text</font></span></font></p>`,
            contentAfter: `<p><font style="color: red;"><span style="color: blue;"><font style="color: red;">text</font></span></font></p>`,
        });
    });

    test("should detect semantic formatting tags as redundant when parent already has that visual formatting", async () => {
        const { el, editor } = await setupEditor("<p><br></p>");
        const { isRedundantElement } = editor.shared.format;
        el.innerHTML = `<p style="font-weight: bold;"><b>boldText</b><i>italicText</i><u>underlineText</u></p>`;
        const pElement = el.firstChild;
        const b = pElement.childNodes[0];
        const i = pElement.childNodes[1];
        const u = pElement.childNodes[2];

        expect(isRedundantElement(b)).toBe(true);
        expect(isRedundantElement(i)).toBe(false);
        expect(isRedundantElement(u)).toBe(false);
    });

    test("should detect nested small tags as redundant", async () => {
        const { el, editor } = await setupEditor("<p><br></p>");
        const { isRedundantElement } = editor.shared.format;
        el.innerHTML = `<p><small><small>small text</small></small></p>`;
        const outerSmall = el.firstChild.firstChild;
        const innerSmall = outerSmall.firstChild;

        expect(isRedundantElement(outerSmall)).toBe(false);
        expect(isRedundantElement(innerSmall)).toBe(true);
    });

    test("should detect strong tag inside a visually-bold parent via class as redundant", async () => {
        const { el, editor } = await setupEditor("<p><br></p>", {
            styleContent: ".boldClass { font-weight: bold; }",
        });
        const { isRedundantElement } = editor.shared.format;
        el.innerHTML = `<p class="boldClass"><strong>bold text</strong></p>`;
        const strong = el.firstChild.firstChild;

        expect(isRedundantElement(strong)).toBe(true);
    });

    test("should evaluate empty span/font (0 attributes) as redundant only inside the exact same tag", async () => {
        const { el, editor } = await setupEditor("<p><br></p>");
        const { isRedundantElement } = editor.shared.format;
        el.innerHTML = `<span><span>nested span</span></span>`;
        const innerSpan = el.firstChild.firstChild;
        expect(isRedundantElement(innerSpan)).toBe(true);

        el.innerHTML = `<font><span>nested different tag</span></font>`;
        const innerSpanInFont = el.firstChild.firstChild;
        expect(isRedundantElement(innerSpanInFont)).toBe(false);
    });

    test("should return false for span/font containing exotic attributes like id, data-*, lang", async () => {
        const { el, editor } = await setupEditor("<p><br></p>");
        const { isRedundantElement } = editor.shared.format;
        el.innerHTML = `<p style="color: red;"><span style="color: red;" id="my-span" data-test="123" lang="en">text</span></p>`;
        const span = el.firstChild.firstChild;

        expect(isRedundantElement(span)).toBe(false);
    });

    test("should detect inline style matching parent computed style as redundant", async () => {
        const { el, editor } = await setupEditor("<p><br></p>");
        const { isRedundantElement } = editor.shared.format;
        el.innerHTML = `<div style="color: rgb(255, 0, 0);"><span style="color: red;">text</span></div>`;
        const span = el.firstChild.firstChild;

        expect(isRedundantElement(span)).toBe(true);
    });

    test("should reject redundancy for intermediate style overrides", async () => {
        const { el, editor } = await setupEditor("<p><br></p>");
        const { isRedundantElement } = editor.shared.format;
        el.innerHTML = `<font style="color: red;"><span style="color: blue;"><font style="color: red;">text</font></span></font>`;
        const middleSpan = el.firstChild.firstChild;
        const innerFont = middleSpan.firstChild;

        expect(isRedundantElement(middleSpan)).toBe(false);
        expect(isRedundantElement(innerFont)).toBe(false);
    });

    test("should detect color class already covered by ancestor span or font as redundant", async () => {
        const { el, editor } = await setupEditor("<p><br></p>");
        const { isRedundantElement } = editor.shared.format;
        el.innerHTML = `<span class="text-danger"><span class="text-danger">danger text</span></span>`;
        const innerSpan = el.firstChild.firstChild;

        expect(isRedundantElement(innerSpan)).toBe(true);
    });

    test("should reject redundancy when color class is overridden by a different class of same category on intermediate ancestor", async () => {
        const { el, editor } = await setupEditor("<p><br></p>");
        const { isRedundantElement } = editor.shared.format;
        el.innerHTML = `<span class="text-danger"><span class="text-primary"><span class="text-danger">text</span></span></span>`;
        const middleSpan = el.firstChild.firstChild;
        const innerSpan = middleSpan.firstChild;

        expect(isRedundantElement(middleSpan)).toBe(false);
        expect(isRedundantElement(innerSpan)).toBe(false);
    });

    test("should return false when node classes are not all recognized color classes", async () => {
        const { el, editor } = await setupEditor("<p><br></p>");
        const { isRedundantElement } = editor.shared.format;
        el.innerHTML = `<span class="text-danger"><span class="text-danger my-custom-class">text</span></span>`;
        const innerSpan = el.firstChild.firstChild;

        expect(isRedundantElement(innerSpan)).toBe(false);
    });

    test("should require both inline styles and color classes to be redundant when both are present", async () => {
        const { el, editor } = await setupEditor("<p><br></p>");
        const { isRedundantElement } = editor.shared.format;
        el.innerHTML = `<span style="color: red;" class="text-danger"><span style="color: red;" class="text-primary">text</span></span>`;
        const innerSpan = el.firstChild.firstChild;

        expect(isRedundantElement(innerSpan)).toBe(false);
    });
});

describe("Editor config initialization", () => {
    test("should replace empty content by a default baseContainer, even if not provided in the config", async () => {
        await testEditor({
            config: { content: "" },
            contentAfter: "<p><br></p>",
        });
    });
});

describe("table normalization", () => {
    test("should add the cells missing from a ragged table without altering the spans", async () => {
        await testEditor({
            contentBefore: unformat(`
                <table>
                    <tbody>
                        <tr>
                            <td rowspan="2" colspan="2">A</td>
                            <td>B</td>
                        </tr>
                        <tr>
                            <td>C</td>
                        </tr>
                        <tr>
                            <td>D</td>
                        </tr>
                    </tbody>
                </table>
            `),
            contentAfter: unformat(`
                <table>
                    <tbody>
                        <tr>
                            <td rowspan="2" colspan="2">A</td>
                            <td>B</td>
                        </tr>
                        <tr>
                            <td>C</td>
                        </tr>
                        <tr>
                            <td>D</td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>
            `),
        });
    });

    test("should add the header cells missing from a ragged table", async () => {
        await testEditor({
            contentBefore: unformat(`
                <table>
                    <tbody>
                        <tr>
                            <th class="o_table_header">Second Header</th>
                        </tr>
                        <tr>
                            <td>Content Cell</td>
                            <td>Content Cell</td>
                        </tr>
                    </tbody>
                </table>
            `),
            contentAfter: unformat(`
                <table>
                    <tbody>
                        <tr>
                            <th class="o_table_header"><p><br></p></th>
                            <th class="o_table_header">Second Header</th>
                        </tr>
                        <tr>
                            <td>Content Cell</td>
                            <td>Content Cell</td>
                        </tr>
                    </tbody>
                </table>
            `),
        });
    });

    test("should add the cells missing from the first and the last rows", async () => {
        await testEditor({
            contentBefore: unformat(
                `<table><tbody><tr><td>B</td></tr><tr><td>C</td><td>D</td></tr><tr><td>E</td></tr></tbody></table>`
            ),
            contentAfter: unformat(
                `<table><tbody><tr><td><p><br></p></td><td>B</td></tr><tr><td>C</td><td>D</td></tr><tr><td>E</td><td><p><br></p></td></tr></tbody></table>`
            ),
        });
    });
});
