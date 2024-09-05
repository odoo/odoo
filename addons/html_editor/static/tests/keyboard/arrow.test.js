import { describe, expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "../_helpers/editor";
import { tick } from "@odoo/hoot-mock";
import { simulateArrowKeyPress } from "../_helpers/user_actions";
import { getContent, setSelection } from "../_helpers/selection";

const keyPress = (keys) => async (editor) => {
    await simulateArrowKeyPress(editor, keys);
    // Allow onselectionchange handler to run.
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
});

describe("Around icons", () => {
    test("should move past the icon (ArrowRight)", async () => {
        await testEditor({
            contentBefore: `<p>abc[]<span class="fa fa-music"></span>def</p>`,
            contentBeforeEdit: `<p>abc[]<span class="fa fa-music" contenteditable="false">\u200b</span>def</p>`,
            stepFunction: keyPress("ArrowRight"),
            contentAfterEdit: `<p>abc<span class="fa fa-music" contenteditable="false">\u200b</span>[]def</p>`,
            contentAfter: `<p>abc<span class="fa fa-music"></span>[]def</p>`,
        });
    });
    test("should move past the icon (ArrowLeft)", async () => {
        await testEditor({
            contentBefore: `<p>abc<span class="fa fa-music"></span>[]def</p>`,
            contentBeforeEdit: `<p>abc<span class="fa fa-music" contenteditable="false">\u200b</span>[]def</p>`,
            stepFunction: keyPress("ArrowLeft"),
            contentAfterEdit: `<p>abc[]<span class="fa fa-music" contenteditable="false">\u200b</span>def</p>`,
            contentAfter: `<p>abc[]<span class="fa fa-music"></span>def</p>`,
        });
    });
});

describe("Selection correction when it lands at the editable root", () => {
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
                '<p>[]<br></p><hr contenteditable="false">' +
                '<hr contenteditable="false"><p><br></p>',
            stepFunction: keyPress("ArrowRight"),
            contentAfter: "<p><br></p><hr>" + "<hr><p>[]<br></p>",
        });
    });

    test("should place cursor before the first separator", async () => {
        await testEditor({
            contentBefore:
                '<p><br></p><hr contenteditable="false">' +
                '<hr contenteditable="false"><p>[]<br></p>',
            stepFunction: keyPress("ArrowLeft"),
            contentAfter: "<p>[]<br></p><hr>" + "<hr><p><br></p>",
        });
    });
});

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
        const content = "<p>" + "الرجال" + '<a href="#">اءيتجنب</a>' + "هؤلاء" + "</p>";
        // Displayed as "هؤلاء<a href="#">اءيتجنب</a>الرجال" in the editor:
        //                third +         link      + first
        test("should move into a link (ArrowLeft)", async () => {
            const { editor, el } = await setupEditor(content, { config: { direction: "rtl" } });
            const pFirstChild = el.firstChild.firstChild; // "الرجال"
            // childNodes[1] and childNodes[3] are the ZWNBSP text nodes
            const link = el.firstChild.childNodes[2];
            // Place cursor at the end of first child (before the FEFF char)
            // Displayed as هؤلاء\uFEFF<a href="#">\uFEFFاءيتجنب\uFEFF</a>\uFEFF[]الرجال
            setSelection({ anchorNode: pFirstChild, anchorOffset: pFirstChild.length });

            await keyPress("ArrowLeft")(editor);

            const selection = editor.document.getSelection();
            expect(selection.anchorNode).toBe(link.firstChild); // FEFF node
            expect(selection.anchorOffset).toBe(1);
            // Displayed as هؤلاء\uFEFF<a href="#">\uFEFFاءيتجنب[]\uFEFF</a>\uFEFFالرجال
            expect(getContent(el)).toBe(
                '<p>الرجال\uFEFF<a href="#" class="o_link_in_selection">\uFEFF[]اءيتجنب\uFEFF</a>\uFEFFهؤلاء</p>'
            );
        });
        test("should move into a link (ArrowRight)", async () => {
            const { editor, el } = await setupEditor(content, { config: { direction: "rtl" } });
            // childNodes[1] and childNodes[3] are the ZWNBSP text nodes
            const link = el.firstChild.childNodes[2];
            const pFifthChild = el.firstChild.childNodes[4]; // "هؤلاء"
            const link2ndChild = link.childNodes[1]; // اءيتجنب
            // Place cursor at the beginning of fifth child (after the FEFF char)
            // Displayed as هؤلاء[]\uFEFF<a href="#">\uFEFFاءيتجنب\uFEFF</a>\uFEFFالرجال
            setSelection({ anchorNode: pFifthChild, anchorOffset: 0 });

            await keyPress("ArrowRight")(editor);

            const selection = editor.document.getSelection();
            expect(selection.anchorNode).toBe(link2ndChild);
            expect(selection.anchorOffset).toBe(link2ndChild.length);
            // Displayed as هؤلاء\uFEFF<a href="#">\uFEFF[]اءيتجنب\uFEFF</a>\uFEFFالرجال
            expect(getContent(el)).toBe(
                '<p>الرجال\uFEFF<a href="#" class="o_link_in_selection">\uFEFFاءيتجنب[]\uFEFF</a>\uFEFFهؤلاء</p>'
            );
        });
        test("should move out of a link (ArrowLeft)", async () => {
            const { editor, el } = await setupEditor(content, { config: { direction: "rtl" } });
            // childNodes[1] and childNodes[3] are the ZWNBSP text nodes
            const link = el.firstChild.childNodes[2];
            const link2ndChild = link.childNodes[1]; // text content inside link: اءيتجنب
            // Place cursor at the end of link's content (before the FEFF char)
            // Displayed as هؤلاء\uFEFF<a href="#">\uFEFF[]اءيتجنب\uFEFF</a>\uFEFFالرجال
            setSelection({ anchorNode: link2ndChild, anchorOffset: link2ndChild.length });

            await keyPress("ArrowLeft")(editor);

            const selection = editor.document.getSelection();
            expect(selection.anchorNode).toBe(el.firstChild.childNodes[3]); // FEFF node outside link
            expect(selection.anchorOffset).toBe(1);
            // Displayed as هؤلاء[]\uFEFF<a href="#">\uFEFFاءيتجنب\uFEFF</a>\uFEFFالرجال
            expect(getContent(el)).toBe(
                '<p>الرجال\uFEFF<a href="#">\uFEFFاءيتجنب\uFEFF</a>\uFEFF[]هؤلاء</p>'
            );
        });
        test("should move out of a link (ArrowRight)", async () => {
            const { editor, el } = await setupEditor(content, { config: { direction: "rtl" } });
            // childNodes[1] and childNodes[3] are the ZWNBSP text nodes
            const pFirstChild = el.firstChild.firstChild; // "الرجال"
            const link = el.firstChild.childNodes[2];
            const link2ndChild = link.childNodes[1]; // text content inside link: اءيتجنب
            // Place cursor at the beginning of link's content (after the FEFF char)
            // Displayed as هؤلاء\uFEFF<a href="#">\uFEFFاءيتجنب[]\uFEFF</a>\uFEFFالرجال
            setSelection({ anchorNode: link2ndChild, anchorOffset: 0 });

            await keyPress("ArrowRight")(editor);

            const selection = editor.document.getSelection();
            expect(selection.anchorNode).toBe(pFirstChild);
            expect(selection.anchorOffset).toBe(pFirstChild.length);
            // Displayed as هؤلاء\uFEFF<a href="#">\uFEFFاءيتجنب\uFEFF</a>\uFEFF[]الرجال
            expect(getContent(el)).toBe(
                '<p>الرجال[]\uFEFF<a href="#">\uFEFFاءيتجنب\uFEFF</a>\uFEFFهؤلاء</p>'
            );
        });
    });
});
