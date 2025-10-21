import { describe, expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "../_helpers/editor";
import { tick } from "@odoo/hoot-mock";
import { press } from "@odoo/hoot-dom";
import { simulateArrowKeyPress } from "../_helpers/user_actions";
import { getContent, setSelection } from "../_helpers/selection";
import { unformat } from "../_helpers/format";

const keyPress = (keys) => async (editor) => {
    await simulateArrowKeyPress(editor, keys);
    // Allow onselectionchange handler to run.
    await tick();
    await tick();
};

describe("Around ZWS", () => {
    test("should move past a zws (collapsed - ArrowRight)", async () => {
        await testEditor({
            contentBefore: '<p>ab[]<span class="a">\u200B</span>cd</p>',
            stepFunction: keyPress("ArrowRight"),
            contentAfter: '<p>ab<span class="a">\u200B</span>c[]d</p>',
        });
        await testEditor({
            contentBefore: '<p>ab<span class="a">[]\u200B</span>cd</p>',
            stepFunction: keyPress("ArrowRight"),
            contentAfter: '<p>ab<span class="a">\u200B</span>c[]d</p>',
        });
    });

    test.tags("focus required");
    test("should move past a zws (collapsed - ArrowLeft)", async () => {
        await testEditor({
            contentBefore: '<p>ab<span class="a">\u200B[]</span>cd</p>',
            stepFunction: keyPress("ArrowLeft"),
            contentAfter: '<p>a[]b<span class="a">\u200B</span>cd</p>',
        });
        await testEditor({
            contentBefore: '<p>ab<span class="a">\u200B</span>[]cd</p>',
            stepFunction: keyPress("ArrowLeft"),
            contentAfter: '<p>a[]b<span class="a">\u200B</span>cd</p>',
        });
        await testEditor({
            contentBefore:
                '<p><span class="a">\u200B</span></p><p><span class="b">[]\u200B</span>ab</p>',
            stepFunction: keyPress("ArrowLeft"),
            contentAfter:
                '<p><span class="a">\u200B[]</span></p><p><span class="b">\u200B</span>ab</p>',
        });
        await testEditor({
            contentBefore:
                '<p><span class="a">\u200B</span></p><p><span class="b">\u200B[]</span></p>',
            stepFunction: keyPress("ArrowLeft"),
            contentAfter:
                '<p><span class="a">\u200B[]</span></p><p><span class="b">\u200B</span></p>',
        });
    });

    test("should move past a zws (collapsed at the end of a block)", async () => {
        await testEditor({
            contentBefore: '<p>ab[]<span class="a">\u200B</span></p><p>cd</p>',
            stepFunction: keyPress("ArrowRight"),
            contentAfter: '<p>ab<span class="a">\u200B</span></p><p>[]cd</p>',
        });
        await testEditor({
            contentBefore: '<p>ab<span class="a">[]\u200B</span></p><p>cd</p>',
            stepFunction: keyPress("ArrowRight"),
            contentAfter: '<p>ab<span class="a">\u200B</span></p><p>[]cd</p>',
        });
        await testEditor({
            contentBefore:
                '<p>ab<span class="a">\u200B[]</span></p><p><span class="b">\u200B</span></p>',
            stepFunction: keyPress("ArrowRight"),
            contentAfter:
                '<p>ab<span class="a">\u200B</span></p><p><span class="b">[]\u200B</span></p>',
        });
        await testEditor({
            contentBefore:
                '<p>ab<span class="a">[]\u200B</span></p><p><span class="b">\u200B</span></p>',
            stepFunction: keyPress("ArrowRight"),
            contentAfter:
                '<p>ab<span class="a">\u200B</span></p><p><span class="b">[]\u200B</span></p>',
        });
    });

    test("should select a zws", async () => {
        await testEditor({
            contentBefore: '<p>[ab]<span class="a">\u200B</span>cd</p>',
            stepFunction: keyPress(["Shift", "ArrowRight"]),
            contentAfter: '<p>[ab<span class="a">\u200B</span>c]d</p>',
        });
        await testEditor({
            contentBefore: '<p>[ab<span class="a">]\u200B</span>cd</p>',
            stepFunction: keyPress(["Shift", "ArrowRight"]),
            contentAfter: '<p>[ab<span class="a">\u200B</span>c]d</p>',
        });
    });

    test("should select a zws (2)", async () => {
        await testEditor({
            contentBefore: '<p>a[b]<span class="a">\u200B</span>cd</p>',
            stepFunction: keyPress(["Shift", "ArrowRight"]),
            contentAfter: '<p>a[b<span class="a">\u200B</span>c]d</p>',
        });
        await testEditor({
            contentBefore: '<p>a[b<span class="a">]\u200B</span>cd</p>',
            stepFunction: keyPress(["Shift", "ArrowRight"]),
            contentAfter: '<p>a[b<span class="a">\u200B</span>c]d</p>',
        });
        await testEditor({
            contentBefore:
                '<p>a[b]<span class="a">\u200B</span></p><p><span class="b">\u200B</span></p>',
            stepFunction: keyPress(["Shift", "ArrowRight"]),
            contentAfter:
                '<p>a[b<span class="a">\u200B</span></p><p>]<span class="b">\u200B</span></p>',
        });
    });

    test("should select a zws (3)", async () => {
        await testEditor({
            contentBefore: '<p>ab[]<span class="a">\u200B</span>cd</p>',
            stepFunction: keyPress(["Shift", "ArrowRight"]),
            contentAfter: '<p>ab<span class="a">[\u200B</span>c]d</p>',
        });
        await testEditor({
            contentBefore: '<p>ab<span class="a">[]\u200B</span>cd</p>',
            stepFunction: keyPress(["Shift", "ArrowRight"]),
            contentAfter: '<p>ab<span class="a">[\u200B</span>c]d</p>',
        });
    });

    test("should select a zws backwards (ArrowLeft)", async () => {
        await testEditor({
            contentBefore: '<p>ab<span class="a">\u200B[]</span>cd</p>',
            stepFunction: keyPress(["Shift", "ArrowLeft"]),
            contentAfter: '<p>a]b<span class="a">\u200B[</span>cd</p>',
        });
        await testEditor({
            contentBefore: '<p>ab<span class="a">\u200B</span>[]cd</p>',
            stepFunction: keyPress(["Shift", "ArrowLeft"]),
            contentAfter: '<p>a]b<span class="a">\u200B[</span>cd</p>',
        });
    });

    test("should select a zws backwards (ArrowLeft - 2)", async () => {
        await testEditor({
            contentBefore: '<p>ab<span class="a">\u200B</span>]cd[</p>',
            stepFunction: keyPress(["Shift", "ArrowLeft"]),
            contentAfter: '<p>a]b<span class="a">\u200B</span>cd[</p>',
        });
        await testEditor({
            contentBefore: '<p>ab<span class="a">\u200B]</span>cd[</p>',
            stepFunction: keyPress(["Shift", "ArrowLeft"]),
            contentAfter: '<p>a]b<span class="a">\u200B</span>cd[</p>',
        });
    });

    test("should select a zws backwards (ArrowLeft - 3)", async () => {
        await testEditor({
            contentBefore: '<p>ab<span class="a">\u200B</span>]c[d</p>',
            stepFunction: keyPress(["Shift", "ArrowLeft"]),
            contentAfter: '<p>a]b<span class="a">\u200B</span>c[d</p>',
        });
        await testEditor({
            contentBefore: '<p>ab<span class="a">\u200B]</span>c[d</p>',
            stepFunction: keyPress(["Shift", "ArrowLeft"]),
            contentAfter: '<p>a]b<span class="a">\u200B</span>c[d</p>',
        });
    });

    test("should select a zws backwards (ArrowRight)", async () => {
        await testEditor({
            contentBefore: '<p>ab<span class="a">]\u200B[</span>cd</p>',
            stepFunction: keyPress(["Shift", "ArrowRight"]),
            contentAfter: '<p>ab<span class="a">\u200B</span>[c]d</p>',
        });
        await testEditor({
            contentBefore: '<p>ab<span class="a">]\u200B</span>[cd</p>',
            stepFunction: keyPress(["Shift", "ArrowRight"]),
            contentAfter: '<p>ab<span class="a">\u200B</span>[c]d</p>',
        });
        await testEditor({
            contentBefore: '<p>ab]<span class="a">\u200B</span>[cd</p>',
            stepFunction: keyPress(["Shift", "ArrowRight"]),
            contentAfter: '<p>ab<span class="a">\u200B</span>[c]d</p>',
        });
        await testEditor({
            contentBefore: '<p>ab]<span class="a">\u200B[</span>cd</p>',
            stepFunction: keyPress(["Shift", "ArrowRight"]),
            contentAfter: '<p>ab<span class="a">\u200B</span>[c]d</p>',
        });
    });

    test("should select a zws backwards (ArrowRight - 2)", async () => {
        await testEditor({
            contentBefore: '<p>ab<span class="a">]\u200B</span>c[d</p>',
            stepFunction: keyPress(["Shift", "ArrowRight"]),
            contentAfter: '<p>ab<span class="a">\u200B</span>c[]d</p>',
        });
        await testEditor({
            contentBefore: '<p>ab]<span class="a">\u200B</span>c[d</p>',
            stepFunction: keyPress(["Shift", "ArrowRight"]),
            contentAfter: '<p>ab<span class="a">\u200B</span>c[]d</p>',
        });
    });

    test("should deselect a zws", async () => {
        await testEditor({
            contentBefore: '<p>ab<span class="a">[\u200B]</span>cd</p>',
            stepFunction: keyPress(["Shift", "ArrowLeft"]),
            contentAfter: '<p>a]b[<span class="a">\u200B</span>cd</p>', // Normalized by the browser
        });
        await testEditor({
            contentBefore: '<p>ab<span class="a">[\u200B</span>]cd</p>',
            stepFunction: keyPress(["Shift", "ArrowLeft"]),
            contentAfter: '<p>a]b[<span class="a">\u200B</span>cd</p>', // Normalized by the browser
        });
        await testEditor({
            contentBefore: '<p>ab[<span class="a">\u200B]</span>cd</p>',
            stepFunction: keyPress(["Shift", "ArrowLeft"]),
            contentAfter: '<p>a]b[<span class="a">\u200B</span>cd</p>', // Normalized by the browser
        });
        await testEditor({
            contentBefore: '<p>ab[<span class="a">\u200B</span>]cd</p>',
            stepFunction: keyPress(["Shift", "ArrowLeft"]),
            contentAfter: '<p>a]b[<span class="a">\u200B</span>cd</p>', // Normalized by the browser
        });
    });

    test("should deselect a zws (2)", async () => {
        await testEditor({
            contentBefore: '<p>a[b<span class="a">\u200B]</span>cd</p>',
            stepFunction: keyPress(["Shift", "ArrowLeft"]),
            contentAfter: '<p>a[]b<span class="a">\u200B</span>cd</p>',
        });
        await testEditor({
            contentBefore: '<p>a[b<span class="a">\u200B</span>]cd</p>',
            stepFunction: keyPress(["Shift", "ArrowLeft"]),
            contentAfter: '<p>a[]b<span class="a">\u200B</span>cd</p>',
        });
    });
});

describe("Around links", () => {
    test("should move into a link (ArrowRight)", async () => {
        await testEditor({
            contentBefore: '<p>ab[]<a href="http://test.test/">cd</a>ef</p>',
            contentBeforeEdit:
                "<p>ab[]" +
                "\ufeff" + // before zwnbsp
                '<a href="http://test.test/">' +
                "\ufeff" + // start zwnbsp
                "cd" + // content
                "\ufeff" + // end zwnbsp
                "</a>" +
                "\ufeff" + // after zwnbsp
                "ef</p>",
            stepFunction: keyPress("ArrowRight"),
            contentAfterEdit:
                "<p>ab" +
                "\ufeff" + // before zwnbsp
                '<a href="http://test.test/" class="o_link_in_selection">' +
                "\ufeff" + // start zwnbsp
                "[]cd" + // content
                "\ufeff" + // end zwnbsp
                "</a>" +
                "\ufeff" + // after zwnbsp
                "ef</p>",
            contentAfter: '<p>ab<a href="http://test.test/">[]cd</a>ef</p>',
        });
    });

    test("should move into a link (ArrowLeft)", async () => {
        await testEditor({
            contentBefore: '<p>ab<a href="http://test.test/">cd</a>[]ef</p>',
            contentBeforeEdit:
                "<p>ab" +
                "\ufeff" + // before zwnbsp
                '<a href="http://test.test/">' +
                "\ufeff" + // start zwnbsp
                "cd" + // content
                "\ufeff" + // end zwnbsp
                "</a>" +
                "\ufeff" + // after zwnbsp
                "[]ef</p>",
            stepFunction: keyPress("ArrowLeft"),
            contentAfterEdit:
                "<p>ab" +
                "\ufeff" + // before zwnbsp
                '<a href="http://test.test/" class="o_link_in_selection">' +
                "\ufeff" + // start zwnbsp
                "cd[]" + // content
                "\ufeff" + // end zwnbsp
                "</a>" +
                "\ufeff" + // after zwnbsp
                "ef</p>",
            contentAfter: '<p>ab<a href="http://test.test/">cd[]</a>ef</p>',
        });
    });

    test("should move out of a link (ArrowRight)", async () => {
        await testEditor({
            contentBefore: '<p>ab<a href="http://test.test/">cd[]</a>ef</p>',
            contentBeforeEdit:
                "<p>ab" +
                "\ufeff" + // before zwnbsp
                '<a href="http://test.test/" class="o_link_in_selection">' +
                "\ufeff" + // start zwnbsp
                "cd[]" + // content
                "\ufeff" + // end zwnbsp
                "</a>" +
                "\ufeff" + // after zwnbsp
                "ef</p>",
            stepFunction: keyPress("ArrowRight"),
            contentAfterEdit:
                "<p>ab" +
                "\ufeff" + // before zwnbsp
                '<a href="http://test.test/">' +
                "\ufeff" + // start zwnbsp
                "cd" + // content
                "\ufeff" + // end zwnbsp
                "</a>" +
                "\ufeff" + // after zwnbsp
                "[]ef</p>",
            contentAfter: '<p>ab<a href="http://test.test/">cd</a>[]ef</p>',
        });
    });

    test("should move out of a link (ArrowLeft)", async () => {
        await testEditor({
            contentBefore: '<p>ab<a href="http://test.test/">[]cd</a>ef</p>',
            contentBeforeEdit:
                "<p>ab" +
                "\ufeff" + // before zwnbsp
                '<a href="http://test.test/" class="o_link_in_selection">' +
                "\ufeff" + // start zwnbsp
                "[]cd" + // content
                "\ufeff" + // end zwnbsp
                "</a>" +
                "\ufeff" + // after zwnbsp
                "ef</p>",
            stepFunction: keyPress("ArrowLeft"),
            contentAfterEdit:
                "<p>ab[]" +
                "\ufeff" + // before zwnbsp
                '<a href="http://test.test/">' +
                "\ufeff" + // start zwnbsp
                "cd" + // content
                "\ufeff" + // end zwnbsp
                "</a>" +
                "\ufeff" + // after zwnbsp
                "ef</p>",
            contentAfter: '<p>ab[]<a href="http://test.test/">cd</a>ef</p>',
        });
    });
});

describe("Around icons", () => {
    test("should correctly move cursor over icons (ArrowRight)", async () => {
        await testEditor({
            contentBefore: `<p>abc[]<span class="fa fa-music"></span>def</p>`,
            contentBeforeEdit: `<p>abc[]\ufeff<span class="fa fa-music" contenteditable="false">\u200b</span>\ufeffdef</p>`,
            stepFunction: keyPress("ArrowRight"),
            contentAfterEdit: `<p>abc\ufeff<span class="fa fa-music" contenteditable="false">\u200b</span>[]\ufeffdef</p>`,
            contentAfter: `<p>abc<span class="fa fa-music"></span>[]def</p>`,
        });
        await testEditor({
            contentBefore: `<p><span class="fa fa-music"></span>[]<span class="fa fa-music"></span></p><p><br></p>`,
            contentBeforeEdit: `<p>\ufeff<span class="fa fa-music" contenteditable="false">\u200b</span>\ufeff[]<span class="fa fa-music" contenteditable="false">\u200b</span>\ufeff</p><p><br></p>`,
            stepFunction: keyPress("ArrowRight"),
            contentAfterEdit: `<p>\ufeff<span class="fa fa-music" contenteditable="false">\u200b</span>\ufeff<span class="fa fa-music" contenteditable="false">\u200b</span>[]\ufeff</p><p><br></p>`,
            contentAfter: `<p><span class="fa fa-music"></span><span class="fa fa-music"></span>[]</p><p><br></p>`,
        });
        await testEditor({
            contentBefore: `<p><span class="fa fa-music"></span>[]<br><span class="fa fa-music"></span></p><p><br></p>`,
            contentBeforeEdit: `<p>\ufeff<span class="fa fa-music" contenteditable="false">\u200b</span>\ufeff[]<br>\ufeff<span class="fa fa-music" contenteditable="false">\u200b</span>\ufeff</p><p><br></p>`,
            stepFunction: keyPress("ArrowRight"),
            contentAfterEdit: `<p>\ufeff<span class="fa fa-music" contenteditable="false">\u200b</span>\ufeff<br>\ufeff[]<span class="fa fa-music" contenteditable="false">\u200b</span>\ufeff</p><p><br></p>`,
            contentAfter: `<p><span class="fa fa-music"></span><br>[]<span class="fa fa-music"></span></p><p><br></p>`,
        });
    });
    test("should correctly move cursor over icons (ArrowLeft)", async () => {
        await testEditor({
            contentBefore: `<p>abc<span class="fa fa-music"></span>[]def</p>`,
            contentBeforeEdit: `<p>abc\ufeff<span class="fa fa-music" contenteditable="false">\u200b</span>\ufeff[]def</p>`,
            stepFunction: keyPress("ArrowLeft"),
            contentAfterEdit: `<p>abc\ufeff[]<span class="fa fa-music" contenteditable="false">\u200b</span>\ufeffdef</p>`,
            contentAfter: `<p>abc[]<span class="fa fa-music"></span>def</p>`,
        });
        await testEditor({
            contentBefore: `<p><span class="fa fa-music"></span><br><span class="fa fa-music"></span>[]</p>`,
            contentBeforeEdit: `<p>\ufeff<span class="fa fa-music" contenteditable="false">\u200b</span>\ufeff<br>\ufeff<span class="fa fa-music" contenteditable="false">\u200b</span>\ufeff[]</p>`,
            stepFunction: keyPress("ArrowLeft"),
            contentAfterEdit: `<p>\ufeff<span class="fa fa-music" contenteditable="false">\u200b</span>\ufeff<br>\ufeff[]<span class="fa fa-music" contenteditable="false">\u200b</span>\ufeff</p>`,
            contentAfter: `<p><span class="fa fa-music"></span><br>[]<span class="fa fa-music"></span></p>`,
        });
    });
    test("should correctly move cursor over icons (ArrowUp)", async () => {
        await testEditor({
            contentBefore: `<p><br></p><p><span class="fa fa-music"></span></p><p>[]<br></p>`,
            contentBeforeEdit: `<p><br></p><p>\ufeff<span class="fa fa-music" contenteditable="false">\u200b</span>\ufeff</p><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`,
            stepFunction: keyPress("ArrowUp"),
            contentAfterEdit: `<p><br></p><p>[]\ufeff<span class="fa fa-music" contenteditable="false">\u200b</span>\ufeff</p><p><br></p>`,
            contentAfter: `<p><br></p><p>[]<span class="fa fa-music"></span></p><p><br></p>`,
        });
        await testEditor({
            contentBefore: `<p><br></p><p><span class="fa fa-music"></span><br>[]<span class="fa fa-music"></span></p>`,
            contentBeforeEdit: `<p><br></p><p>\ufeff<span class="fa fa-music" contenteditable="false">\u200b</span>\ufeff<br>\ufeff[]<span class="fa fa-music" contenteditable="false">\u200b</span>\ufeff</p>`,
            stepFunction: keyPress("ArrowDown"),
            contentAfterEdit: `<p><br></p><p>\ufeff<span class="fa fa-music" contenteditable="false">\u200b</span>\ufeff<br>\ufeff<span class="fa fa-music" contenteditable="false">\u200b</span>\ufeff[]</p>`,
            contentAfter: `<p><br></p><p><span class="fa fa-music"></span><br><span class="fa fa-music"></span>[]</p>`,
        });
    });
    test("should correctly move cursor over icons (ArrowDown)", async () => {
        await testEditor({
            contentBefore: `<p>[]<br></p><p><span class="fa fa-music"></span></p><p><br></p>`,
            contentBeforeEdit: `<p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p><p>\ufeff<span class="fa fa-music" contenteditable="false">\u200b</span>\ufeff</p><p><br></p>`,
            stepFunction: keyPress("ArrowDown"),
            contentAfterEdit: `<p><br></p><p>[]\ufeff<span class="fa fa-music" contenteditable="false">\u200b</span>\ufeff</p><p><br></p>`,
            contentAfter: `<p><br></p><p>[]<span class="fa fa-music"></span></p><p><br></p>`,
        });
        await testEditor({
            contentBefore: `<p>[]<span class="fa fa-music"></span><br><span class="fa fa-music"></span></p><p><br></p>`,
            contentBeforeEdit: `<p>\ufeff[]<span class="fa fa-music" contenteditable="false">\u200b</span>\ufeff<br>\ufeff<span class="fa fa-music" contenteditable="false">\u200b</span>\ufeff</p><p><br></p>`,
            stepFunction: keyPress("ArrowDown"),
            contentAfterEdit: `<p>\ufeff<span class="fa fa-music" contenteditable="false">\u200b</span>\ufeff<br>[]\ufeff<span class="fa fa-music" contenteditable="false">\u200b</span>\ufeff</p><p><br></p>`,
            contentAfter: `<p><span class="fa fa-music"></span><br>[]<span class="fa fa-music"></span></p><p><br></p>`,
        });
    });
});

describe("Selection correction when it lands at the editable root", () => {
    test("should place cursor between two tables (1)", async () => {
        await testEditor({
            contentBefore:
                "<table><tbody><tr><td><p>a</p><p>b[]</p></td></tr></tbody></table>" +
                "<table><tbody><tr><td><p>c</p><p>d</p></td></tr></tbody></table>",
            stepFunction: keyPress("ArrowRight"),
            contentAfterEdit:
                '<p data-selection-placeholder=""><br></p>' +
                "<table><tbody><tr><td><p>a</p><p>b</p></td></tr></tbody></table>" +
                `<p data-selection-placeholder="" o-we-hint-text='Type "/" for commands' class="o-we-hint o-horizontal-caret">[]<br></p>` +
                "<table><tbody><tr><td><p>c</p><p>d</p></td></tr></tbody></table>" +
                '<p data-selection-placeholder=""><br></p>',
            contentAfter:
                "<table><tbody><tr><td><p>a</p><p>b</p></td></tr></tbody></table>" +
                "[]" +
                "<table><tbody><tr><td><p>c</p><p>d</p></td></tr></tbody></table>",
        });
    });

    test.tags("focus required");
    test("should place cursor between two tables (2)", async () => {
        await testEditor({
            contentBefore:
                "<table><tbody><tr><td><p>a</p><p>b</p></td></tr></tbody></table>" +
                "<table><tbody><tr><td><p>[]c</p><p>d</p></td></tr></tbody></table>",
            stepFunction: keyPress("ArrowLeft"),
            contentAfterEdit:
                '<p data-selection-placeholder=""><br></p>' +
                "<table><tbody><tr><td><p>a</p><p>b</p></td></tr></tbody></table>" +
                `<p data-selection-placeholder="" o-we-hint-text='Type "/" for commands' class="o-we-hint o-horizontal-caret">[]<br></p>` +
                "<table><tbody><tr><td><p>c</p><p>d</p></td></tr></tbody></table>" +
                '<p data-selection-placeholder=""><br></p>',
            contentAfter:
                "<table><tbody><tr><td><p>a</p><p>b</p></td></tr></tbody></table>" +
                "[]" +
                "<table><tbody><tr><td><p>c</p><p>d</p></td></tr></tbody></table>",
        });
    });

    test("should place cursor in the paragraph below", async () => {
        await testEditor({
            contentBefore:
                "<table><tbody><tr><td><p>a</p><p>b[]</p></td></tr></tbody></table>" +
                "<p><br></p>",
            stepFunction: keyPress("ArrowRight"),
            contentAfter:
                "<table><tbody><tr><td><p>a</p><p>b</p></td></tr></tbody></table>" +
                "<p>[]<br></p>",
        });
    });

    test("should place cursor in the paragraph above", async () => {
        await testEditor({
            contentBefore:
                "<p><br></p>" +
                "<table><tbody><tr><td><p>[]a</p><p>b</p></td></tr></tbody></table>",
            stepFunction: keyPress("ArrowLeft"),
            contentAfter:
                "<p>[]<br></p>" +
                "<table><tbody><tr><td><p>a</p><p>b</p></td></tr></tbody></table>",
        });
    });

    test("should move cursor to safe space (avoid reaching the editable root) (1)", async () => {
        await testEditor({
            contentBefore: "<table><tbody><tr><td><p>a</p><p>b[]</p></td></tr></tbody></table>",
            stepFunction: keyPress("ArrowRight"),
            contentAfterEdit:
                '<p data-selection-placeholder=""><br></p>' +
                "<table><tbody><tr><td><p>a</p><p>b</p></td></tr></tbody></table>" +
                `<p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`,
        });
    });
    test("should move cursor to safe space (avoid reaching the editable root) (2)", async () => {
        await testEditor({
            contentBefore: "<table><tbody><tr><td><p>[]a</p><p>b</p></td></tr></tbody></table>",
            stepFunction: keyPress("ArrowLeft"),
            contentAfterEdit:
                `<p data-selection-placeholder="" o-we-hint-text='Type "/" for commands' class="o-we-hint o-horizontal-caret">[]<br></p>` +
                "<table><tbody><tr><td><p>a</p><p>b</p></td></tr></tbody></table>" +
                '<p data-selection-placeholder=""><br></p>',
        });
    });

    test("should place cursor after the second separator", async () => {
        await testEditor({
            contentBefore:
                "<p>[]<br></p>" +
                '<hr contenteditable="false">' +
                '<hr contenteditable="false">' +
                "<p><br></p>",
            stepFunction: keyPress("ArrowRight"),
            contentAfterEdit:
                "<p><br></p>" +
                '<hr contenteditable="false">' +
                `<p data-selection-placeholder="" o-we-hint-text='Type "/" for commands' class="o-we-hint o-horizontal-caret">[]<br></p>` +
                '<hr contenteditable="false">' +
                "<p><br></p>",
            contentAfter: "<p><br></p><hr>[]<hr><p><br></p>",
        });
    });

    test.tags("focus required");
    test("should place cursor before the first separator", async () => {
        await testEditor({
            contentBefore:
                "<p><br></p>" +
                '<hr contenteditable="false">' +
                '<hr contenteditable="false">' +
                "<p>[]<br></p>",
            stepFunction: keyPress("ArrowLeft"),
            contentAfterEdit:
                "<p><br></p>" +
                '<hr contenteditable="false">' +
                `<p data-selection-placeholder="" o-we-hint-text='Type "/" for commands' class="o-we-hint o-horizontal-caret">[]<br></p>` +
                '<hr contenteditable="false">' +
                "<p><br></p>",
            contentAfter: "<p><br></p><hr>[]<hr><p><br></p>",
        });
    });
});

describe.tags("focus required");
describe("Around invisible chars in RTL languages", () => {
    describe("ZWS", () => {
        const content = "<p>" + "الرجال" + '<span class="a">\u200B</span>' + "هؤلاء" + "</p>";
        // Displayed as " هؤلاء<span class="a">\u200B</span>الرجال" in the editor:
        //                third +               span +      first
        test("should move past the zws (ArrowLeft)", async () => {
            const { editor, el } = await setupEditor(content, { config: { direction: "rtl" } });
            const pFirstChild = el.firstChild.firstChild; // "الرجال"
            const pThirdChild = el.firstChild.childNodes[2]; // "هؤلاء"
            // Place cursor at the end of first child (next to the span)
            // Displayed as هؤلاء<span class="a">\u200B</span>[]الرجال
            setSelection({ anchorNode: pFirstChild, anchorOffset: pFirstChild.length });

            await keyPress("ArrowLeft")(editor);

            const selection = editor.document.getSelection();
            expect(selection.anchorNode).toBe(pThirdChild);
            expect(selection.anchorOffset).toBe(1);
            // Displayed as ه[]ؤلاء<span class="a">\u200B</span>الرجال
            expect(getContent(el)).toBe('<p>الرجال<span class="a">\u200B</span>ه[]ؤلاء</p>');
        });
        test("should move past the zws (ArrowRight)", async () => {
            const { editor, el } = await setupEditor(content, { config: { direction: "rtl" } });
            const pFirstChild = el.firstChild.firstChild; // "الرجال"
            const pThirdChild = el.firstChild.childNodes[2]; // "هؤلاء"
            // Place cursor at the beginning of third child (next to the span)
            // Displayed as هؤلاء[]<span class="a">\u200B</span>الرجال
            setSelection({ anchorNode: pThirdChild, anchorOffset: 0 });

            await keyPress("ArrowRight")(editor);

            const selection = editor.document.getSelection();
            expect(selection.anchorNode).toBe(pFirstChild);
            expect(selection.anchorOffset).toBe(pFirstChild.length - 1);
            // Displayed as هؤلاء<span class="a">\u200B</span>الرجا[]ل
            expect(getContent(el)).toBe('<p>الرجا[]ل<span class="a">\u200B</span>هؤلاء</p>');
        });
    });

    describe("ZWNBSP", () => {
        const content =
            "<p>" + "الرجال" + '<a href="http://test.test/">اءيتجنب</a>' + "هؤلاء" + "</p>";
        // Displayed as "هؤلاء<a href="http://test.test/">اءيتجنب</a>الرجال" in the editor:
        //                third +         link      + first
        test("should move into a link (ArrowLeft)", async () => {
            const { editor, el } = await setupEditor(content, { config: { direction: "rtl" } });
            const pFirstChild = el.firstChild.firstChild; // "الرجال"
            // childNodes[1] and childNodes[3] are the ZWNBSP text nodes
            const link = el.firstChild.childNodes[2];
            // Place cursor at the end of first child (before the FEFF char)
            // Displayed as هؤلاء\uFEFF<a href="http://test.test/">\uFEFFاءيتجنب\uFEFF</a>\uFEFF[]الرجال
            setSelection({ anchorNode: pFirstChild, anchorOffset: pFirstChild.length });

            await keyPress("ArrowLeft")(editor);

            const selection = editor.document.getSelection();
            expect(selection.anchorNode).toBe(link.firstChild); // FEFF node
            expect(selection.anchorOffset).toBe(1);
            // Displayed as هؤلاء\uFEFF<a href="http://test.test/">\uFEFFاءيتجنب[]\uFEFF</a>\uFEFFالرجال
            expect(getContent(el)).toBe(
                '<p>الرجال\uFEFF<a href="http://test.test/" class="o_link_in_selection">\uFEFF[]اءيتجنب\uFEFF</a>\uFEFFهؤلاء</p>'
            );
        });
        test("should move into a link (ArrowRight)", async () => {
            const { editor, el } = await setupEditor(content, { config: { direction: "rtl" } });
            // childNodes[1] and childNodes[3] are the ZWNBSP text nodes
            const link = el.firstChild.childNodes[2];
            const pFifthChild = el.firstChild.childNodes[4]; // "هؤلاء"
            const link2ndChild = link.childNodes[1]; // اءيتجنب
            // Place cursor at the beginning of fifth child (after the FEFF char)
            // Displayed as هؤلاء[]\uFEFF<a href="http://test.test/">\uFEFFاءيتجنب\uFEFF</a>\uFEFFالرجال
            setSelection({ anchorNode: pFifthChild, anchorOffset: 0 });

            await keyPress("ArrowRight")(editor);

            const selection = editor.document.getSelection();
            expect(selection.anchorNode).toBe(link2ndChild);
            expect(selection.anchorOffset).toBe(link2ndChild.length);
            // Displayed as هؤلاء\uFEFF<a href="http://test.test/">\uFEFF[]اءيتجنب\uFEFF</a>\uFEFFالرجال
            expect(getContent(el)).toBe(
                '<p>الرجال\uFEFF<a href="http://test.test/" class="o_link_in_selection">\uFEFFاءيتجنب[]\uFEFF</a>\uFEFFهؤلاء</p>'
            );
        });
        test("should move out of a link (ArrowLeft)", async () => {
            const { editor, el } = await setupEditor(content, { config: { direction: "rtl" } });
            // childNodes[1] and childNodes[3] are the ZWNBSP text nodes
            const link = el.firstChild.childNodes[2];
            const link2ndChild = link.childNodes[1]; // text content inside link: اءيتجنب
            // Place cursor at the end of link's content (before the FEFF char)
            // Displayed as هؤلاء\uFEFF<a href="http://test.test/">\uFEFF[]اءيتجنب\uFEFF</a>\uFEFFالرجال
            setSelection({ anchorNode: link2ndChild, anchorOffset: link2ndChild.length });

            await keyPress("ArrowLeft")(editor);

            const selection = editor.document.getSelection();
            expect(selection.anchorNode).toBe(el.firstChild.childNodes[3]); // FEFF node outside link
            expect(selection.anchorOffset).toBe(1);
            // Displayed as هؤلاء[]\uFEFF<a href="http://test.test/">\uFEFFاءيتجنب\uFEFF</a>\uFEFFالرجال
            expect(getContent(el)).toBe(
                '<p>الرجال\uFEFF<a href="http://test.test/">\uFEFFاءيتجنب\uFEFF</a>\uFEFF[]هؤلاء</p>'
            );
        });
        test("should move out of a link (ArrowRight)", async () => {
            const { editor, el } = await setupEditor(content, { config: { direction: "rtl" } });
            // childNodes[1] and childNodes[3] are the ZWNBSP text nodes
            const pFirstChild = el.firstChild.firstChild; // "الرجال"
            const link = el.firstChild.childNodes[2];
            const link2ndChild = link.childNodes[1]; // text content inside link: اءيتجنب
            // Place cursor at the beginning of link's content (after the FEFF char)
            // Displayed as هؤلاء\uFEFF<a href="http://test.test/">\uFEFFاءيتجنب[]\uFEFF</a>\uFEFFالرجال
            setSelection({ anchorNode: link2ndChild, anchorOffset: 0 });

            await keyPress("ArrowRight")(editor);

            const selection = editor.document.getSelection();
            expect(selection.anchorNode).toBe(pFirstChild);
            expect(selection.anchorOffset).toBe(pFirstChild.length);
            // Displayed as هؤلاء\uFEFF<a href="http://test.test/">\uFEFFاءيتجنب\uFEFF</a>\uFEFF[]الرجال
            expect(getContent(el)).toBe(
                '<p>الرجال[]\uFEFF<a href="http://test.test/">\uFEFFاءيتجنب\uFEFF</a>\uFEFFهؤلاء</p>'
            );
        });
    });
});

describe("Around contenteditable false elements containing contenteditable true elements", () => {
    test("should select contenteditable false element (ArrowRight)", async () => {
        await testEditor({
            contentBefore: unformat(`
                <p>abc</p>
                <p>de[f]</p>
                <div contenteditable="false">
                    <div contenteditable="true">
                        <p>ghi</p>
                        <p>jkl</p>
                    </div>
                </div>
                <p>mno</p>
            `),
            stepFunction: () => press(["shift", "arrowright"]),
            contentAfterEdit: unformat(`
                <p>abc</p>
                <p>de[f</p>
                <div contenteditable="false">
                    <div contenteditable="true">
                        <p>ghi</p>
                        <p>jkl</p>
                    </div>
                </div>
                <p>]mno</p>
            `),
        });
    });
    test("should select contenteditable false element (ArrowLeft)", async () => {
        await testEditor({
            contentBefore: unformat(`
                <p>abc</p>
                <p>def</p>
                <div contenteditable="false">
                    <div contenteditable="true">
                        <p>ghi</p>
                        <p>jkl</p>
                    </div>
                </div>
                <p>]m[no</p>
            `),
            stepFunction: () => press(["shift", "arrowleft"]),
            contentAfter: unformat(`
                <p>abc</p>
                <p>def]</p>
                <div contenteditable="false">
                    <div contenteditable="true">
                        <p>ghi</p>
                        <p>jkl</p>
                    </div>
                </div>
                <p>m[no</p>
            `),
        });
    });
    test("should select contenteditable false element (ArrowUp)", async () => {
        await testEditor({
            contentBefore: unformat(`
                <p>abc</p>
                <p>def</p>
                <div contenteditable="false">
                    <div contenteditable="true">
                        <p>ghi</p>
                        <p>jkl</p>
                    </div>
                </div>
                <p>]mno[</p>
            `),
            stepFunction: () => press(["shift", "arrowup"]),
            contentAfter: unformat(`
                <p>abc</p>
                <p>def]</p>
                <div contenteditable="false">
                    <div contenteditable="true">
                        <p>ghi</p>
                        <p>jkl</p>
                    </div>
                </div>
                <p>mno[</p>
            `),
        });
    });
    test("should select contenteditable false element (ArrowDown)", async () => {
        await testEditor({
            contentBefore: unformat(`
                <p>abc</p>
                <p>[def]</p>
                <div contenteditable="false">
                    <div contenteditable="true">
                        <p>ghi</p>
                        <p>jkl</p>
                    </div>
                </div>
                <p>mno</p>
            `),
            stepFunction: () => press(["shift", "arrowdown"]),
            contentAfter: unformat(`
                <p>abc</p>
                <p>[def</p>
                <div contenteditable="false">
                    <div contenteditable="true">
                        <p>ghi</p>
                        <p>jkl</p>
                    </div>
                </div>
                <p>]mno</p>
            `),
        });
    });
});
