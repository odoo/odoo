import { test } from "@odoo/hoot";
import { testEditor } from "../_helpers/editor";
import { tick } from "@odoo/hoot-mock";
import { simulateArrowKeyPress } from "../_helpers/user_actions";

const keyPress = (keys) => async (editor) => {
    simulateArrowKeyPress(editor, keys);
    // Allow onselectionchange handler to run.
    await tick();
};

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
        contentBefore: '<p><span class="a">\u200B</span></p><p><span class="b">\u200B[]</span></p>',
        stepFunction: keyPress("ArrowLeft"),
        contentAfter: '<p><span class="a">\u200B[]</span></p><p><span class="b">\u200B</span></p>',
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

test("should move into a link (ArrowRight)", async () => {
    await testEditor({
        contentBefore: '<p>ab[]<a href="#">cd</a>ef</p>',
        contentBeforeEdit:
            "<p>ab[]" +
            "\ufeff" + // before zwnbsp
            '<a href="#">' +
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
            '<a href="#" class="o_link_in_selection">' +
            "\ufeff" + // start zwnbsp
            "[]cd" + // content
            "\ufeff" + // end zwnbsp
            "</a>" +
            "\ufeff" + // after zwnbsp
            "ef</p>",
        contentAfter: '<p>ab<a href="#">[]cd</a>ef</p>',
    });
});

test("should move into a link (ArrowLeft)", async () => {
    await testEditor({
        contentBefore: '<p>ab<a href="#">cd</a>[]ef</p>',
        contentBeforeEdit:
            "<p>ab" +
            "\ufeff" + // before zwnbsp
            '<a href="#">' +
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
            '<a href="#" class="o_link_in_selection">' +
            "\ufeff" + // start zwnbsp
            "cd[]" + // content
            "\ufeff" + // end zwnbsp
            "</a>" +
            "\ufeff" + // after zwnbsp
            "ef</p>",
        contentAfter: '<p>ab<a href="#">cd[]</a>ef</p>',
    });
});

test("should move out of a link (ArrowRight)", async () => {
    await testEditor({
        contentBefore: '<p>ab<a href="#">cd[]</a>ef</p>',
        contentBeforeEdit:
            "<p>ab" +
            "\ufeff" + // before zwnbsp
            '<a href="#" class="o_link_in_selection">' +
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
            '<a href="#">' +
            "\ufeff" + // start zwnbsp
            "cd" + // content
            "\ufeff" + // end zwnbsp
            "</a>" +
            "\ufeff" + // after zwnbsp
            "[]ef</p>",
        contentAfter: '<p>ab<a href="#">cd</a>[]ef</p>',
    });
});

test("should move out of a link (ArrowLeft)", async () => {
    await testEditor({
        contentBefore: '<p>ab<a href="#">[]cd</a>ef</p>',
        contentBeforeEdit:
            "<p>ab" +
            "\ufeff" + // before zwnbsp
            '<a href="#" class="o_link_in_selection">' +
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
            '<a href="#">' +
            "\ufeff" + // start zwnbsp
            "cd" + // content
            "\ufeff" + // end zwnbsp
            "</a>" +
            "\ufeff" + // after zwnbsp
            "ef</p>",
        contentAfter: '<p>ab[]<a href="#">cd</a>ef</p>',
    });
});

test("should place cursor in the table below", async () => {
    await testEditor({
        contentBefore:
            "<table><tbody><tr><td><p>a</p><p>b[]</p></td></tr></tbody></table>" +
            "<table><tbody><tr><td><p>c</p><p>d</p></td></tr></tbody></table>",
        stepFunction: keyPress("ArrowRight"),
        contentAfter:
            "<table><tbody><tr><td><p>a</p><p>b</p></td></tr></tbody></table>" +
            "<table><tbody><tr><td><p>[]c</p><p>d</p></td></tr></tbody></table>",
    });
});

test("should place cursor in the table above", async () => {
    await testEditor({
        contentBefore:
            "<table><tbody><tr><td><p>a</p><p>b</p></td></tr></tbody></table>" +
            "<table><tbody><tr><td><p>[]c</p><p>d</p></td></tr></tbody></table>",
        stepFunction: keyPress("ArrowLeft"),
        contentAfter:
            "<table><tbody><tr><td><p>a</p><p>b[]</p></td></tr></tbody></table>" +
            "<table><tbody><tr><td><p>c</p><p>d</p></td></tr></tbody></table>",
    });
});

test("should place cursor in the paragraph below", async () => {
    await testEditor({
        contentBefore:
            "<table><tbody><tr><td><p>a</p><p>b[]</p></td></tr></tbody></table>" + "<p><br></p>",
        stepFunction: keyPress("ArrowRight"),
        contentAfter:
            "<table><tbody><tr><td><p>a</p><p>b</p></td></tr></tbody></table>" + "<p>[]<br></p>",
    });
});

test("should place cursor in the paragraph above", async () => {
    await testEditor({
        contentBefore:
            "<p><br></p>" + "<table><tbody><tr><td><p>[]a</p><p>b</p></td></tr></tbody></table>",
        stepFunction: keyPress("ArrowLeft"),
        contentAfter:
            "<p>[]<br></p>" + "<table><tbody><tr><td><p>a</p><p>b</p></td></tr></tbody></table>",
    });
});

test("should keep cursor at the same position (avoid reaching the editable root) (1)", async () => {
    await testEditor({
        contentBefore: "<table><tbody><tr><td><p>a</p><p>b[]</p></td></tr></tbody></table>",
        stepFunction: keyPress("ArrowRight"),
        contentAfter: "<table><tbody><tr><td><p>a</p><p>b[]</p></td></tr></tbody></table>",
    });
});
test("should keep cursor at the same position (avoid reaching the editable root) (2)", async () => {
    await testEditor({
        contentBefore: "<table><tbody><tr><td><p>[]a</p><p>b</p></td></tr></tbody></table>",
        stepFunction: keyPress("ArrowLeft"),
        contentAfter: "<table><tbody><tr><td><p>[]a</p><p>b</p></td></tr></tbody></table>",
    });
});

test("should place cursor after the second separator", async () => {
    await testEditor({
        contentBefore:
            '<p>[]<br></p><hr contenteditable="false">' + '<hr contenteditable="false"><p><br></p>',
        stepFunction: keyPress("ArrowRight"),
        contentAfter: "<p><br></p><hr>" + "<hr><p>[]<br></p>",
    });
});

test("should place cursor before the first separator", async () => {
    await testEditor({
        contentBefore:
            '<p><br></p><hr contenteditable="false">' + '<hr contenteditable="false"><p>[]<br></p>',
        stepFunction: keyPress("ArrowLeft"),
        contentAfter: "<p>[]<br></p><hr>" + "<hr><p><br></p>",
    });
});
