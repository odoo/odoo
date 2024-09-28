import { describe, expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { getContent } from "../_helpers/selection";
import { insertText, toggleCheckList } from "../_helpers/user_actions";

describe("Range collapsed", () => {
    describe("Insert", () => {
        test("should turn an empty paragraph into a checklist", async () => {
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                stepFunction: toggleCheckList,
                contentAfter: '<ul class="o_checklist"><li>[]<br></li></ul>',
            });
        });

        test("should turn a paragraph into a checklist", async () => {
            await testEditor({
                contentBefore: "<p>ab[]cd</p>",
                stepFunction: toggleCheckList,
                contentAfter: '<ul class="o_checklist"><li>ab[]cd</li></ul>',
            });
        });

        test("should turn a ordered list into a checklist", async () => {
            await testEditor({
                contentBefore: "<ol><li>ab[]cd</li></ol>",
                stepFunction: toggleCheckList,
                contentAfter: '<ul class="o_checklist"><li>ab[]cd</li></ul>',
            });
        });

        test("should turn a unordered list into a checklist", async () => {
            await testEditor({
                contentBefore: "<ul><li>ab[]cd</li></ul>",
                stepFunction: toggleCheckList,
                contentAfter: '<ul class="o_checklist"><li>ab[]cd</li></ul>',
            });
        });

        test("should turn a heading into a checklist", async () => {
            await testEditor({
                contentBefore: "<h1>ab[]cd</h1>",
                stepFunction: toggleCheckList,
                contentAfter: '<ul class="o_checklist"><li><h1>ab[]cd</h1></li></ul>',
            });
        });

        test("should turn an empty heading into a checklist and display the right hint", async () => {
            const { el, editor } = await setupEditor("<h1>[]</h1>");
            expect(getContent(el)).toBe(`<h1 placeholder="Heading 1" class="o-we-hint">[]</h1>`);

            toggleCheckList(editor);
            expect(getContent(el)).toBe(
                `<ul class="o_checklist"><li><h1 placeholder="Heading 1" class="o-we-hint">[]</h1></li></ul>`
            );

            await insertText(editor, "a");
            editor.dispatch("NORMALIZE", { node: el });
            expect(getContent(el)).toBe(`<ul class="o_checklist"><li><h1>a[]</h1></li></ul>`);
        });

        test("should turn a paragraph in a div into a checklist", async () => {
            await testEditor({
                contentBefore: "<div><p>ab[]cd</p></div>",
                stepFunction: toggleCheckList,
                contentAfter: '<div><ul class="o_checklist"><li>ab[]cd</li></ul></div>',
            });
        });

        test("should turn a paragraph with formats into a checklist", async () => {
            await testEditor({
                contentBefore: "<p><span><b>ab</b></span> <span><i>cd</i></span> ef[]gh</p>",
                stepFunction: toggleCheckList,
                contentAfter:
                    '<ul class="o_checklist"><li><span><b>ab</b></span> <span><i>cd</i></span> ef[]gh</li></ul>',
            });
        });

        test("should turn a paragraph between 2 checklist into a checklist item", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li class="o_checked">abc</li></ul><p>d[]ef</p><ul class="o_checklist"><li class="o_checked">ghi</li></ul>',
                stepFunction: toggleCheckList,
                contentAfter:
                    '<ul class="o_checklist"><li class="o_checked">abc</li><li>d[]ef</li><li class="o_checked">ghi</li></ul>',
            });
        });

        test("should turn a unordered list into a checklist between 2 checklists inside a checklist", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li class="o_checked">abc</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">def</li>
                            </ul>
                        </li>
                        <li class="oe-nested">
                            <ul>
                                <li>g[]hi</li>
                            </ul>
                        </li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">jkl</li>
                            </ul>
                        </li>
                    </ul>`),
                stepFunction: toggleCheckList,
                /* @todo @phoenix: move this test case to a new file, with tests for checkitem IDs.
                contentAfterEdit: unformat(`
                    <ul class="o_checklist">
                        <li class="o_checked" id="checkId-1">abc</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked" id="checkId-2">def</li>
                                <li id="checkId-4">g[]hi</li>
                                <li class="o_checked" id="checkId-3">jkl</li>
                            </ul>
                        </li>
                    </ul>`), */
                contentAfterEdit: unformat(`
                    <ul class="o_checklist">
                        <li class="o_checked">abc</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">def</li>
                                <li>g[]hi</li>
                                <li class="o_checked">jkl</li>
                            </ul>
                        </li>
                    </ul>`),
            });
            await testEditor({
                contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li class="o_checked">abc</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">def</li>
                            </ul>
                        </li>
                        <li class="oe-nested">
                            <ul>
                                <li class="a">g[]hi</li>
                            </ul>
                        </li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">jkl</li>
                            </ul>
                        </li>
                    </ul>`),
                stepFunction: toggleCheckList,
                contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li class="o_checked">abc</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">def</li>
                                <li class="a">g[]hi</li>
                                <li class="o_checked">jkl</li>
                            </ul>
                        </li>
                    </ul>`),
            });
        });

        test("should remove the list-style when change the list style", async () => {
            await testEditor({
                contentBefore: unformat(`
                        <ul>
                            <li style="list-style: cambodian;">a[]</li>
                        </ul>`),
                stepFunction: toggleCheckList,
                contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li>a[]</li>
                    </ul>`),
            });
        });

        test("should turn an empty paragraph of multiple table cells into a checklist", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <table class="table table-bordered">
                        <tbody>
                            <tr>
                                <td>[<br></td>
                                <td><br></td>
                                <td><br></td>
                            </tr>
                            <tr>
                                <td><br></td>
                                <td><br></td>
                                <td><br>]</td>
                            </tr>
                        </tbody>
                    </table>
                `),
                stepFunction: toggleCheckList,
                contentAfterEdit: unformat(`
                    <table class="table table-bordered o_selected_table">
                        <tbody>
                            <tr>
                                <td class="o_selected_td"><ul class="o_checklist"><li>[<br></li></ul></td>
                                <td class="o_selected_td"><ul class="o_checklist"><li><br></li></ul></td>
                                <td class="o_selected_td"><ul class="o_checklist"><li><br></li></ul></td>
                            </tr>
                            <tr>
                                <td class="o_selected_td"><ul class="o_checklist"><li><br></li></ul></td>
                                <td class="o_selected_td"><ul class="o_checklist"><li><br></li></ul></td>
                                <td class="o_selected_td"><ul class="o_checklist"><li>]<br></li></ul></td>
                            </tr>
                        </tbody>
                    </table>
                `),
                contentAfter: unformat(`
                    <table class="table table-bordered">
                        <tbody>
                            <tr>
                                <td><ul class="o_checklist"><li>[<br></li></ul></td>
                                <td><ul class="o_checklist"><li><br></li></ul></td>
                                <td><ul class="o_checklist"><li><br></li></ul></td>
                            </tr>
                            <tr>
                                <td><ul class="o_checklist"><li><br></li></ul></td>
                                <td><ul class="o_checklist"><li><br></li></ul></td>
                                <td><ul class="o_checklist"><li>]<br></li></ul></td>
                            </tr>
                        </tbody>
                    </table>
                `),
            });
        });

        test("should create a new checked list if current node is inside a nav-item list", async () => {
            await testEditor({
                contentBefore: '<ul><li class="nav-item">a[]b</li></ul>',
                stepFunction: toggleCheckList,
                contentAfter:
                    '<ul><li class="nav-item"><ul class="o_checklist"><li>a[]b</li></ul></li></ul>',
            });
        });

        test("should create a new checked list if closestBlock is inside a nav-item list", async () => {
            await testEditor({
                contentBefore: '<ul><li class="nav-item"><div><p>a[]b</p></div></li></ul>',
                stepFunction: toggleCheckList,
                contentAfter:
                    '<ul><li class="nav-item"><div><ul class="o_checklist"><li>a[]b</li></ul></div></li></ul>',
            });
        });

        test("should only keep dir attribute when converting a non Paragraph element", async () => {
            await testEditor({
                contentBefore: '<h1 dir="rtl" class="h1">a[]b</h1>',
                stepFunction: toggleCheckList,
                contentAfter:
                    '<ul class="o_checklist" dir="rtl"><li><h1 dir="rtl" class="h1">a[]b</h1></li></ul>',
            });
        });

        test("should keep all attributes when converting a Paragraph element", async () => {
            await testEditor({
                contentBefore: '<p dir="rtl" class="text-uppercase">a[]b</p>',
                stepFunction: toggleCheckList,
                contentAfter: '<ul class="o_checklist text-uppercase" dir="rtl"><li>a[]b</li></ul>',
            });
        });
    });
    describe("Remove", () => {
        test("should turn an empty list into a paragraph", async () => {
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li>[]<br></li></ul>',
                stepFunction: toggleCheckList,
                contentAfter: "<p>[]<br></p>",
            });
        });

        test("should turn a checklist into a paragraph", async () => {
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li>ab[]cd</li></ul>',
                stepFunction: toggleCheckList,
                contentAfter: "<p>ab[]cd</p>",
            });
        });

        test("should turn a checklist into a heading", async () => {
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li><h1>ab[]cd</h1></li></ul>',
                stepFunction: toggleCheckList,
                contentAfter: "<h1>ab[]cd</h1>",
            });
        });

        test("should turn a checklist item into a paragraph", async () => {
            await testEditor({
                contentBefore: '<p>ab</p><ul class="o_checklist"><li>cd</li><li>ef[]gh</li></ul>',
                stepFunction: toggleCheckList,
                contentAfter: '<p>ab</p><ul class="o_checklist"><li>cd</li></ul><p>ef[]gh</p>',
            });
        });

        test("should turn a checklist with formats into a paragraph", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li><span><b>ab</b></span> <span><i>cd</i></span> ef[]gh</li></ul>',
                stepFunction: toggleCheckList,
                contentAfter: "<p><span><b>ab</b></span> <span><i>cd</i></span> ef[]gh</p>",
            });
        });

        test("should turn nested list items into paragraphs", async () => {
            await testEditor({
                contentBefore: unformat(`
                        <ul class="o_checklist">
                            <li class="o_checked">a</li>
                            <li class="oe-nested">
                                <ul class="o_checklist">
                                    <li class="o_checked">[]b</li>
                                </ul>
                            </li>
                            <li class="oe-nested">
                                <ul class="o_checklist">
                                    <li class="oe-nested">
                                        <ul class="o_checklist">
                                            <li class="o_checked">c</li>
                                        </ul>
                                    </li>
                                </ul>
                            </li>
                        </ul>`),
                stepFunction: toggleCheckList,
                contentAfter: unformat(`
                        <ul class="o_checklist">
                            <li class="o_checked">a</li>
                        </ul>
                        <p>[]b</p>
                        <ul class="o_checklist">
                            <li class="oe-nested">
                                <ul class="o_checklist">
                                    <li class="oe-nested">
                                        <ul class="o_checklist">
                                            <li class="o_checked">c</li>
                                        </ul>
                                    </li>
                                </ul>
                            </li>
                        </ul>`),
            });
        });

        test("should turn an list of multiple table cells into a empty paragraph", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <table class="table table-bordered">
                        <tbody>
                            <tr>
                                <td>[<ul class="o_checklist"><li><br></li></ul></td>
                                <td><ul class="o_checklist"><li><br></li></ul></td>
                                <td><ul class="o_checklist"><li><br></li></ul></td>
                            </tr>
                            <tr>
                                <td><ul class="o_checklist"><li><br></li></ul></td>
                                <td><ul class="o_checklist"><li><br></li></ul></td>
                                <td><ul class="o_checklist"><li><br></li></ul>]</td>
                            </tr>
                        </tbody>
                    </table>
                `),
                stepFunction: toggleCheckList,
                contentAfterEdit: unformat(`
                    <table class="table table-bordered o_selected_table">
                        <tbody>
                            <tr>
                                <td class="o_selected_td">[<p><br></p></td>
                                <td class="o_selected_td"><p><br></p></td>
                                <td class="o_selected_td"><p><br></p></td>
                            </tr>
                            <tr>
                                <td class="o_selected_td"><p><br></p></td>
                                <td class="o_selected_td"><p><br></p></td>
                                <td class="o_selected_td"><p><br></p>]</td>
                            </tr>
                        </tbody>
                    </table>
                `),
                contentAfter: unformat(`
                    <table class="table table-bordered">
                        <tbody>
                            <tr>
                                <td>[<p><br></p></td>
                                <td><p><br></p></td>
                                <td><p><br></p></td>
                            </tr>
                            <tr>
                                <td><p><br></p></td>
                                <td><p><br></p></td>
                                <td><p><br></p>]</td>
                            </tr>
                        </tbody>
                    </table>
                `),
            });
        });
    });
});

describe("Range not collapsed", () => {
    describe("Insert", () => {
        test("should turn a paragraph into a checklist", async () => {
            await testEditor({
                contentBefore: "<p>ab</p><p>cd[ef]gh</p>",
                stepFunction: toggleCheckList,
                contentAfter: '<p>ab</p><ul class="o_checklist"><li>cd[ef]gh</li></ul>',
            });
        });

        test("should turn a heading into a checklist", async () => {
            await testEditor({
                contentBefore: "<p>ab</p><h1>cd[ef]gh</h1>",
                stepFunction: toggleCheckList,
                contentAfter: '<p>ab</p><ul class="o_checklist"><li><h1>cd[ef]gh</h1></li></ul>',
            });
        });

        test("should turn two paragraphs into a checklist with two items", async () => {
            await testEditor({
                contentBefore: "<p>ab</p><p>cd[ef</p><p>gh]ij</p>",
                stepFunction: toggleCheckList,
                contentAfter: '<p>ab</p><ul class="o_checklist"><li>cd[ef</li><li>gh]ij</li></ul>',
            });
        });

        test("should turn two paragraphs in a div into a checklist with two items", async () => {
            await testEditor({
                contentBefore: "<div><p>ab[cd</p><p>ef]gh</p></div>",
                stepFunction: toggleCheckList,
                contentAfter:
                    '<div><ul class="o_checklist"><li>ab[cd</li><li>ef]gh</li></ul></div>',
            });
        });

        test("should turn a paragraph and a checklist item into two list items", async () => {
            await testEditor({
                contentBefore:
                    '<p>a[b</p><ul class="o_checklist"><li class="o_checked">c]d</li><li>ef</li></ul>',
                stepFunction: toggleCheckList,
                contentAfter:
                    '<ul class="o_checklist"><li>a[b</li><li class="o_checked">c]d</li><li>ef</li></ul>',
            });
            await testEditor({
                contentBefore:
                    '<p>a[b</p><ul class="o_checklist"><li class="o_checked">c]d</li><li class="o_checked">ef</li></ul>',
                stepFunction: toggleCheckList,
                contentAfter:
                    '<ul class="o_checklist"><li>a[b</li><li class="o_checked">c]d</li><li class="o_checked">ef</li></ul>',
            });
        });

        test("should turn a checklist item and a paragraph into two list items", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li>ab</li><li class="o_checked">c[d</li></ul><p>e]f</p>',
                stepFunction: toggleCheckList,
                contentAfter:
                    '<ul class="o_checklist"><li>ab</li><li class="o_checked">c[d</li><li>e]f</li></ul>',
            });
        });

        test("should turn a checklist, a paragraph and another list into one list with three list items", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li>a[b</li></ul><p>cd</p><ul class="o_checklist"><li class="o_checked">e]f</li></ul>',
                stepFunction: toggleCheckList,
                contentAfter:
                    '<ul class="o_checklist"><li>a[b</li><li>cd</li><li class="o_checked">e]f</li></ul>',
            });
        });

        test("should turn a checklist item, a paragraph and another list into one list with all three as list items", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li class="o_checked">ab</li><li>c[d</li></ul><p>ef</p><ul class="o_checklist"><li class="o_checked">g]h</li></ul>',
                stepFunction: toggleCheckList,
                contentAfter:
                    '<ul class="o_checklist"><li class="o_checked">ab</li><li>c[d</li><li>ef</li><li class="o_checked">g]h</li></ul>',
            });
        });

        test("should turn a checklist, a paragraph and a checklist item into one list with all three as list items", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li class="o_checked">a[b</li></ul><p>cd</p><ul class="o_checklist"><li class="o_checked">e]f</li><li>gh</li></ul>',
                stepFunction: toggleCheckList,
                contentAfter:
                    '<ul class="o_checklist"><li class="o_checked">a[b</li><li>cd</li><li class="o_checked">e]f</li><li>gh</li></ul>',
            });
        });
    });
    describe("Remove", () => {
        test("should turn a checklist into a paragraph", async () => {
            await testEditor({
                contentBefore: '<p>ab</p><ul class="o_checklist"><li>cd[ef]gh</li></ul>',
                stepFunction: toggleCheckList,
                contentAfter: "<p>ab</p><p>cd[ef]gh</p>",
            });
        });

        test("should turn a checklist into a heading", async () => {
            await testEditor({
                contentBefore: '<p>ab</p><ul class="o_checklist"><li><h1>cd[ef]gh</h1></li></ul>',
                stepFunction: toggleCheckList,
                contentAfter: "<p>ab</p><h1>cd[ef]gh</h1>",
            });
        });

        test("should turn a checklist into two paragraphs", async () => {
            await testEditor({
                contentBefore: '<p>ab</p><ul class="o_checklist"><li>cd[ef</li><li>gh]ij</li></ul>',
                stepFunction: toggleCheckList,
                contentAfter: "<p>ab</p><p>cd[ef</p><p>gh]ij</p>",
            });
        });

        test("should turn a checklist item into a paragraph", async () => {
            await testEditor({
                contentBefore:
                    '<p>ab</p><ul class="o_checklist"><li class="o_checked">cd</li><li class="o_checked">ef[gh]ij</li></ul>',
                stepFunction: toggleCheckList,
                contentAfter:
                    '<p>ab</p><ul class="o_checklist"><li class="o_checked">cd</li></ul><p>ef[gh]ij</p>',
            });
        });
    });
});
