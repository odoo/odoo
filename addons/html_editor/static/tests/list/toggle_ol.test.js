import { describe, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { toggleOrderedList } from "../_helpers/user_actions";

describe("Range collapsed", () => {
    describe("Insert", () => {
        test("should turn an empty paragraph into a list", async () => {
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                contentBeforeEdit: `<p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`,
                stepFunction: toggleOrderedList,
                contentAfterEdit: `<ol><li o-we-hint-text="List" class="o-we-hint">[]<br></li></ol>`,
                contentAfter: "<ol><li>[]<br></li></ol>",
            });
        });

        test("should turn an empty paragraph into a list with shortcut", async () => {
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                stepFunction: () => press(["control", "shift", "7"]),
                contentAfter: "<ol><li>[]<br></li></ol>",
            });
        });

        test("should turn a paragraph into a list", async () => {
            await testEditor({
                contentBefore: "<p>ab[]cd</p>",
                stepFunction: toggleOrderedList,
                contentAfter: "<ol><li>ab[]cd</li></ol>",
            });
        });

        test("should turn a unordered list into a ordered list", async () => {
            await testEditor({
                contentBefore: "<ul><li>ab[]cd</li></ul>",
                stepFunction: toggleOrderedList,
                contentAfter: "<ol><li>ab[]cd</li></ol>",
            });
        });

        test("should turn a checked list into a ordered list", async () => {
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li>ab[]cd</li></ul>',
                stepFunction: toggleOrderedList,
                contentAfter: "<ol><li>ab[]cd</li></ol>",
            });
        });

        test("should turn a unordered list without marker into a ordered list", async () => {
            await testEditor({
                contentBefore: '<ul><li class="oe-nested">ab[]cd</li></ul>',
                stepFunction: toggleOrderedList,
                contentAfter: "<ol><li>ab[]cd</li></ol>",
            });
        });

        test("should turn a checklist without marker into a ordered list", async () => {
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li class="oe-nested">ab[]cd</li></ul>',
                stepFunction: toggleOrderedList,
                contentAfter: "<ol><li>ab[]cd</li></ol>",
            });
        });

        test("should turn a heading into a list", async () => {
            await testEditor({
                contentBefore: "<h1>ab[]cd</h1>",
                stepFunction: toggleOrderedList,
                contentAfter: "<ol><li><h1>ab[]cd</h1></li></ol>",
            });
        });

        test("should turn a paragraph in a div into a list", async () => {
            await testEditor({
                contentBefore: "<div><p>ab[]cd</p></div>",
                stepFunction: toggleOrderedList,
                contentAfter: "<div><ol><li>ab[]cd</li></ol></div>",
            });
        });

        test("should turn a paragraph with formats into a list", async () => {
            await testEditor({
                contentBefore: "<p><span><b>ab</b></span> <span><i>cd</i></span> ef[]gh</p>",
                stepFunction: toggleOrderedList,
                contentAfter:
                    "<ol><li><span><b>ab</b></span> <span><i>cd</i></span> ef[]gh</li></ol>",
            });
        });

        test("should turn an empty paragraph of multiple table cells into a list", async () => {
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
                stepFunction: toggleOrderedList,
                contentAfterEdit: unformat(`
                    <p data-selection-placeholder=""><br></p>
                    <table class="table table-bordered o_selected_table">
                        <tbody>
                            <tr>
                                <td class="o_selected_td"><ol><li>[<br></li></ol></td>
                                <td class="o_selected_td"><ol><li><br></li></ol></td>
                                <td class="o_selected_td"><ol><li><br></li></ol></td>
                            </tr>
                            <tr>
                                <td class="o_selected_td"><ol><li><br></li></ol></td>
                                <td class="o_selected_td"><ol><li><br></li></ol></td>
                                <td class="o_selected_td"><ol><li>]<br></li></ol></td>
                            </tr>
                        </tbody>
                    </table>
                    <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
                `),
                contentAfter: unformat(`
                    <table class="table table-bordered">
                        <tbody>
                            <tr>
                                <td><ol><li>[<br></li></ol></td>
                                <td><ol><li><br></li></ol></td>
                                <td><ol><li><br></li></ol></td>
                            </tr>
                            <tr>
                                <td><ol><li><br></li></ol></td>
                                <td><ol><li><br></li></ol></td>
                                <td><ol><li>]<br></li></ol></td>
                            </tr>
                        </tbody>
                    </table>
                `),
            });
        });

        test("should create a new ordered list if current node is inside a nav-item list", async () => {
            await testEditor({
                contentBefore: '<ul><li class="nav-item">a[]b</li></ul>',
                stepFunction: toggleOrderedList,
                contentAfter: '<ul><li class="nav-item"><ol><li>a[]b</li></ol></li></ul>',
            });
        });

        test("should create a new ordered list if closestBlock is inside a nav-item list", async () => {
            await testEditor({
                contentBefore: '<ul><li class="nav-item"><div><h1>a[]b</h1></div></li></ul>',
                stepFunction: toggleOrderedList,
                contentAfter:
                    '<ul><li class="nav-item"><div><ol><li><h1>a[]b</h1></li></ol></div></li></ul>',
            });
        });

        test("should only keep dir attribute when converting a non Paragraph element", async () => {
            await testEditor({
                contentBefore: '<h1 dir="rtl" class="h1">a[]b</h1>',
                stepFunction: toggleOrderedList,
                contentAfter: '<ol dir="rtl"><li><h1 dir="rtl" class="h1">a[]b</h1></li></ol>',
            });
        });

        test("should keep all attributes when converting a Paragraph element", async () => {
            await testEditor({
                contentBefore: '<p dir="rtl" class="text-uppercase">a[]b</p>',
                stepFunction: toggleOrderedList,
                contentAfter: '<ol dir="rtl" class="text-uppercase"><li>a[]b</li></ol>',
            });
        });

        test("should apply both color and size styles on list item (1)", async () => {
            await testEditor({
                contentBefore:
                    '<p><span style="font-size: 18px;"><font style="color: rgb(255, 0, 0);">[abc]</font></span></p>',
                stepFunction: toggleOrderedList,
                contentAfter:
                    '<ol><li style="color: rgb(255, 0, 0); font-size: 18px;">[abc]</li></ol>',
            });
        });

        test("should apply both color and size styles on list item (2)", async () => {
            await testEditor({
                contentBefore:
                    '<p><b><i><span style="font-size: 18px;"><font style="color: rgb(255, 0, 0);">[abc]</font></span></i></b></p>',
                stepFunction: toggleOrderedList,
                contentAfter:
                    '<ol><li style="color: rgb(255, 0, 0); font-size: 18px;"><b><i>[abc]</i></b></li></ol>',
            });
        });

        test("should not apply color and size styles on list item", async () => {
            await testEditor({
                contentBefore:
                    '<p><span style="font-size: 18px;"><font style="color: rgb(0, 128, 0);">a</font></span>b</p>',
                stepFunction: toggleOrderedList,
                contentAfter:
                    '<ol><li><span style="font-size: 18px;"><font style="color: rgb(0, 128, 0);">a</font></span>b</li></ol>',
            });
        });

        test("should only apply color style on list item", async () => {
            await testEditor({
                contentBefore:
                    '<p><font style="color: rgb(0, 128, 0);"><b><span style="font-size: 18px;">a</span></b><i><span style="font-size: 18px;">a</span></i></font></p>',
                stepFunction: toggleOrderedList,
                contentAfter:
                    '<ol><li style="color: rgb(0, 128, 0);"><b><span style="font-size: 18px;">a</span></b><i><span style="font-size: 18px;">a</span></i></li></ol>',
            });
        });

        test("should only apply size style on list item", async () => {
            await testEditor({
                contentBefore:
                    '<p><span style="font-size: 18px;"><b><font style="color: rgb(0, 128, 0);">a</font></b><i><font style="color: rgb(0, 128, 0);">a</font></i></span></p>',
                stepFunction: toggleOrderedList,
                contentAfter:
                    '<ol><li style="font-size: 18px;"><b><font style="color: rgb(0, 128, 0);">a</font></b><i><font style="color: rgb(0, 128, 0);">a</font></i></li></ol>',
            });
        });
    });
    describe("Remove", () => {
        test("should turn an empty list into a paragraph", async () => {
            await testEditor({
                contentBefore: "<ol><li>[]<br></li></ol>",
                contentBeforeEdit: `<ol><li o-we-hint-text="List" class="o-we-hint">[]<br></li></ol>`,
                stepFunction: toggleOrderedList,
                contentAfterEdit: `<p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`,
                contentAfter: "<p>[]<br></p>",
            });
        });

        test("should turn a list into a paragraph", async () => {
            await testEditor({
                contentBefore: "<ol><li>ab[]cd</li></ol>",
                stepFunction: toggleOrderedList,
                contentAfter: "<p>ab[]cd</p>",
            });
        });

        test("should turn a list into a heading", async () => {
            await testEditor({
                contentBefore: "<ol><li><h1>ab[]cd</h1></li></ol>",
                stepFunction: toggleOrderedList,
                contentAfter: "<h1>ab[]cd</h1>",
            });
        });

        test("should turn a list item into a paragraph", async () => {
            await testEditor({
                contentBefore: "<p>ab</p><ol><li>cd</li><li>ef[]gh</li></ol>",
                stepFunction: toggleOrderedList,
                contentAfter: "<p>ab</p><ol><li>cd</li></ol><p>ef[]gh</p>",
            });
        });

        test("should turn a list with formats into a paragraph", async () => {
            await testEditor({
                contentBefore:
                    "<ol><li><span><b>ab</b></span> <span><i>cd</i></span> ef[]gh</li></ol>",
                stepFunction: toggleOrderedList,
                contentAfter: "<p><span><b>ab</b></span> <span><i>cd</i></span> ef[]gh</p>",
            });
        });

        test("should turn an list of multiple table cells into a empty paragraph", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <table class="table table-bordered">
                        <tbody>
                            <tr>
                                <td>[<ol><li><br></li></ol></td>
                                <td><ol><li><br></li></ol></td>
                                <td><ol><li><br></li></ol></td>
                            </tr>
                            <tr>
                                <td><ol><li><br></li></ol></td>
                                <td><ol><li><br></li></ol></td>
                                <td><ol><li><br></li></ol>]</td>
                            </tr>
                        </tbody>
                    </table>
                `),
                stepFunction: toggleOrderedList,
                contentAfterEdit: unformat(`
                    <p data-selection-placeholder=""><br></p>
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
                    <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
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

        test("should convert list item with line breaks into a single paragraph (1)", async () => {
            await testEditor({
                contentBefore: "<ol><li>ab<br>cd<br>ef[]</li></ol>",
                stepFunction: toggleOrderedList,
                contentAfter: "<p>ab<br>cd<br>ef[]</p>",
            });
        });

        test("should convert list item with line breaks into a single paragraph (2)", async () => {
            await testEditor({
                contentBefore: "<ol><li>ab<br><b>cd</b><br><i>ef[]</i></li></ol>",
                stepFunction: toggleOrderedList,
                contentAfter: "<p>ab<br><b>cd</b><br><i>ef[]</i></p>",
            });
        });
    });
});

describe("Range not collapsed", () => {
    describe("Insert", () => {
        test("should turn a paragraph into a list", async () => {
            await testEditor({
                contentBefore: "<p>ab</p><p>cd[ef]gh</p>",
                stepFunction: toggleOrderedList,
                contentAfter: "<p>ab</p><ol><li>cd[ef]gh</li></ol>",
            });
        });

        test("should turn a paragraph into a list with shortcut", async () => {
            await testEditor({
                contentBefore: "<p>[abc]</p>",
                stepFunction: () => press(["control", "shift", "7"]),
                contentAfter: "<ol><li>[abc]</li></ol>",
            });
        });

        test("should turn a heading into a list", async () => {
            await testEditor({
                contentBefore: "<p>ab</p><h1>cd[ef]gh</h1>",
                stepFunction: toggleOrderedList,
                contentAfter: "<p>ab</p><ol><li><h1>cd[ef]gh</h1></li></ol>",
            });
        });

        test("should turn two paragraphs into a list with two items", async () => {
            await testEditor({
                contentBefore: "<p>ab</p><p>cd[ef</p><p>gh]ij</p>",
                stepFunction: toggleOrderedList,
                contentAfter: "<p>ab</p><ol><li>cd[ef</li><li>gh]ij</li></ol>",
            });
        });

        test("should turn two paragraphs in a div into a list with two items", async () => {
            await testEditor({
                contentBefore: "<div><p>ab[cd</p><p>ef]gh</p></div>",
                stepFunction: toggleOrderedList,
                contentAfter: "<div><ol><li>ab[cd</li><li>ef]gh</li></ol></div>",
            });
        });

        test("should turn a paragraph and a list item into two list items", async () => {
            await testEditor({
                contentBefore: "<p>a[b</p><ol><li>c]d</li><li>ef</li></ol>",
                stepFunction: toggleOrderedList,
                contentAfter: "<ol><li>a[b</li><li>c]d</li><li>ef</li></ol>",
            });
        });

        test("should turn a list item and a paragraph into two list items", async () => {
            await testEditor({
                contentBefore: "<ol><li>ab</li><li>c[d</li></ol><p>e]f</p>",
                stepFunction: toggleOrderedList,
                contentAfter: "<ol><li>ab</li><li>c[d</li><li>e]f</li></ol>",
            });
        });

        test("should turn a list, a paragraph and another list into one list with three list items", async () => {
            await testEditor({
                contentBefore: "<ol><li>a[b</li></ol><p>cd</p><ol><li>e]f</li></ol>",
                stepFunction: toggleOrderedList,
                contentAfter: "<ol><li>a[b</li><li>cd</li><li>e]f</li></ol>",
            });
        });

        test("should turn a list item, a paragraph and another list into one list with all three as list items", async () => {
            await testEditor({
                contentBefore: "<ol><li>ab</li><li>c[d</li></ol><p>ef</p><ol><li>g]h</li></ol>",
                stepFunction: toggleOrderedList,
                contentAfter: "<ol><li>ab</li><li>c[d</li><li>ef</li><li>g]h</li></ol>",
            });
        });

        test("should turn a list, a paragraph and a list item into one list with all three as list items", async () => {
            await testEditor({
                contentBefore: "<ol><li>a[b</li></ol><p>cd</p><ol><li>e]f</li><li>gh</li></ol>",
                stepFunction: toggleOrderedList,
                contentAfter: "<ol><li>a[b</li><li>cd</li><li>e]f</li><li>gh</li></ol>",
            });
        });

        test("should turn a list into an ordered list with text alignment", async () => {
            await testEditor({
                contentBefore:
                    '<ul><li style="text-align: center;">[abc</li><li style="text-align: center;">def]</li></ul>',
                stepFunction: toggleOrderedList,
                contentAfter:
                    '<ol><li style="text-align: center;">[abc</li><li style="text-align: center;">def]</li></ol>',
            });
        });
        test("should apply text-align right when creating ordered list", async () => {
            await testEditor({
                contentBefore: '<p style="text-align: right;">[ab]</p>',
                stepFunction: toggleOrderedList,
                contentAfter: '<ol><li style="text-align: right;">[ab]</li></ol>',
            });
        });
        test("should apply text-align format when creating ordered list from multiple selected blocks", async () => {
            await testEditor({
                contentBefore:
                    '<p style="text-align: right;">[ab</p><p style="text-align: center;">cd]</p>',
                stepFunction: toggleOrderedList,
                contentAfter:
                    '<ol><li style="text-align: right;">[ab</li><li style="text-align: center;">cd]</li></ol>',
            });
        });
    });
    describe("Remove", () => {
        test("should turn a list into a paragraph", async () => {
            await testEditor({
                contentBefore: "<p>ab</p><ol><li>cd[ef]gh</li></ol>",
                stepFunction: toggleOrderedList,
                contentAfter: "<p>ab</p><p>cd[ef]gh</p>",
            });
        });

        test("should turn a list into a heading", async () => {
            await testEditor({
                contentBefore: "<p>ab</p><ol><li><h1>cd[ef]gh</h1></li></ol>",
                stepFunction: toggleOrderedList,
                contentAfter: "<p>ab</p><h1>cd[ef]gh</h1>",
            });
        });

        test("should turn a list into two paragraphs", async () => {
            await testEditor({
                contentBefore: "<p>ab</p><ol><li>cd[ef</li><li>gh]ij</li></ol>",
                stepFunction: toggleOrderedList,
                contentAfter: "<p>ab</p><p>cd[ef</p><p>gh]ij</p>",
            });
        });

        test("should turn a list item into a paragraph", async () => {
            await testEditor({
                contentBefore: "<p>ab</p><ol><li>cd</li><li>ef[gh]ij</li></ol>",
                stepFunction: toggleOrderedList,
                contentAfter: "<p>ab</p><ol><li>cd</li></ol><p>ef[gh]ij</p>",
            });
        });

        test("should turn an ordered list into paragraphs with text alignment", async () => {
            await testEditor({
                contentBefore:
                    '<ol><li style="text-align: center;">[abc</li><li style="text-align: right;">def]</li></ol>',
                stepFunction: toggleOrderedList,
                contentAfter:
                    '<p style="text-align: center;">[abc</p><p style="text-align: right;">def]</p>',
            });
        });
    });
});
