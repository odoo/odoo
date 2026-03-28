import { describe, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { toggleUnorderedList } from "../_helpers/user_actions";

describe("Range collapsed", () => {
    describe("Insert", () => {
        test("should turn an empty paragraph into a list", async () => {
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                contentBeforeEdit: `<p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`,
                stepFunction: toggleUnorderedList,
                contentAfterEdit: `<ul><li o-we-hint-text="List" class="o-we-hint">[]<br></li></ul>`,
                contentAfter: "<ul><li>[]<br></li></ul>",
            });
        });

        test("should turn an empty paragraph into a list with shortcut", async () => {
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                stepFunction: () => press(["control", "shift", "8"]),
                contentAfter: "<ul><li>[]<br></li></ul>",
            });
        });

        test("should turn a paragraph into a list", async () => {
            await testEditor({
                contentBefore: "<p>ab[]cd</p>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<ul><li>ab[]cd</li></ul>",
            });
        });

        test("should turn a ordered list into a unordered list", async () => {
            await testEditor({
                contentBefore: "<ol><li>ab[]cd</li></ol>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<ul><li>ab[]cd</li></ul>",
            });
        });

        test("should turn a checked list into a unordered list", async () => {
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li>ab[]cd</li></ul>',
                stepFunction: toggleUnorderedList,
                contentAfter: "<ul><li>ab[]cd</li></ul>",
            });
        });

        test("should turn a ordered list without marker into an unordered list", async () => {
            await testEditor({
                contentBefore: '<ol><li class="oe-nested">ab[]cd</li></ol>',
                stepFunction: toggleUnorderedList,
                contentAfter: "<ul><li>ab[]cd</li></ul>",
            });
        });

        test("should turn a checklist without marker into a unordered list", async () => {
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li class="oe-nested">ab[]cd</li></ul>',
                stepFunction: toggleUnorderedList,
                contentAfter: "<ul><li>ab[]cd</li></ul>",
            });
        });

        test("should turn a heading into a list", async () => {
            await testEditor({
                contentBefore: "<h1>ab[]cd</h1>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<ul><li><h1>ab[]cd</h1></li></ul>",
            });
        });

        test("should turn a heading into a list (2)", async () => {
            await testEditor({
                contentBefore: "[<h1>abcd</h1>]",
                stepFunction: toggleUnorderedList,
                contentAfter: "<ul><li>[<h1>abcd</h1>]</li></ul>",
            });
        });

        test("should turn a paragraph in a div into a list", async () => {
            await testEditor({
                contentBefore: "<div><p>ab[]cd</p></div>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<div><ul><li>ab[]cd</li></ul></div>",
            });
        });

        test("should turn a paragraph with formats into a list", async () => {
            await testEditor({
                contentBefore: "<p><span><b>ab</b></span> <span><i>cd</i></span> ef[]gh</p>",
                stepFunction: toggleUnorderedList,
                contentAfter:
                    "<ul><li><span><b>ab</b></span> <span><i>cd</i></span> ef[]gh</li></ul>",
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
                stepFunction: toggleUnorderedList,
                contentAfterEdit: unformat(`
                    <p data-selection-placeholder=""><br></p>
                    <table class="table table-bordered o_selected_table">
                        <tbody>
                            <tr>
                                <td class="o_selected_td"><ul><li>[<br></li></ul></td>
                                <td class="o_selected_td"><ul><li><br></li></ul></td>
                                <td class="o_selected_td"><ul><li><br></li></ul></td>
                            </tr>
                            <tr>
                                <td class="o_selected_td"><ul><li><br></li></ul></td>
                                <td class="o_selected_td"><ul><li><br></li></ul></td>
                                <td class="o_selected_td"><ul><li>]<br></li></ul></td>
                            </tr>
                        </tbody>
                    </table>
                    <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
                `),
                contentAfter: unformat(`
                    <table class="table table-bordered">
                        <tbody>
                            <tr>
                                <td><ul><li>[<br></li></ul></td>
                                <td><ul><li><br></li></ul></td>
                                <td><ul><li><br></li></ul></td>
                            </tr>
                            <tr>
                                <td><ul><li><br></li></ul></td>
                                <td><ul><li><br></li></ul></td>
                                <td><ul><li>]<br></li></ul></td>
                            </tr>
                        </tbody>
                    </table>
                `),
            });
        });
        test("should create a new unordered list if current node is inside a nav-item list", async () => {
            await testEditor({
                contentBefore: '<ul><li class="nav-item">a[]b</li></ul>',
                stepFunction: toggleUnorderedList,
                contentAfter: '<ul><li class="nav-item"><ul><li>a[]b</li></ul></li></ul>',
            });
        });

        test("should create a new unordered list if closestBlock is inside a nav-item list", async () => {
            await testEditor({
                contentBefore: '<ul><li class="nav-item"><div><p>a[]b</p></div></li></ul>',
                stepFunction: toggleUnorderedList,
                contentAfter:
                    '<ul><li class="nav-item"><div><ul><li>a[]b</li></ul></div></li></ul>',
            });
        });

        test("should only keep dir attribute when converting a non Paragraph element", async () => {
            await testEditor({
                contentBefore: '<h1 dir="rtl" class="h1">a[]b</h1>',
                stepFunction: toggleUnorderedList,
                contentAfter: '<ul dir="rtl"><li><h1 dir="rtl" class="h1">a[]b</h1></li></ul>',
            });
        });

        test("should keep all attributes when converting a Paragraph element", async () => {
            await testEditor({
                contentBefore: '<p dir="rtl" class="text-uppercase">a[]b</p>',
                stepFunction: toggleUnorderedList,
                contentAfter: '<ul dir="rtl" class="text-uppercase"><li>a[]b</li></ul>',
            });
        });

        test("should apply both color and size styles on list item (1)", async () => {
            await testEditor({
                contentBefore:
                    '<p><span style="font-size: 18px;"><font style="color: rgb(255, 0, 0);">[abc]</font></span></p>',
                stepFunction: toggleUnorderedList,
                contentAfter:
                    '<ul><li style="color: rgb(255, 0, 0); font-size: 18px;">[abc]</li></ul>',
            });
        });

        test("should apply both color and size styles on list item (2)", async () => {
            await testEditor({
                contentBefore:
                    '<p><b><i><span style="font-size: 18px;"><font style="color: rgb(255, 0, 0);">[abc]</font></span></i></b></p>',
                stepFunction: toggleUnorderedList,
                contentAfter:
                    '<ul><li style="color: rgb(255, 0, 0); font-size: 18px;"><b><i>[abc]</i></b></li></ul>',
            });
        });

        test("should not apply color and size styles on list item", async () => {
            await testEditor({
                contentBefore:
                    '<p><span style="font-size: 18px;"><font style="color: rgb(255, 0, 0);">a</font></span>b</p>',
                stepFunction: toggleUnorderedList,
                contentAfter:
                    '<ul><li><span style="font-size: 18px;"><font style="color: rgb(255, 0, 0);">a</font></span>b</li></ul>',
            });
        });

        test("should only apply color style on list item", async () => {
            await testEditor({
                contentBefore:
                    '<p><font style="color: rgb(255, 0, 0);"><b><span style="font-size: 18px;">a</span></b><i><span style="font-size: 18px;">a</span></i></font></p>',
                stepFunction: toggleUnorderedList,
                contentAfter:
                    '<ul><li style="color: rgb(255, 0, 0);"><b><span style="font-size: 18px;">a</span></b><i><span style="font-size: 18px;">a</span></i></li></ul>',
            });
        });

        test("should only apply size style on list item", async () => {
            await testEditor({
                contentBefore:
                    '<p><span style="font-size: 18px;"><b><font style="color: rgb(255, 0, 0);">a</font></b><i><font style="color: rgb(255, 0, 0);">a</font></i></span></p>',
                stepFunction: toggleUnorderedList,
                contentAfter:
                    '<ul><li style="font-size: 18px;"><b><font style="color: rgb(255, 0, 0);">a</font></b><i><font style="color: rgb(255, 0, 0);">a</font></i></li></ul>',
            });
        });
    });
    describe("Remove", () => {
        test("should turn an empty list into a paragraph", async () => {
            await testEditor({
                contentBefore: "<ul><li>[]<br></li></ul>",
                contentBeforeEdit: `<ul><li o-we-hint-text="List" class="o-we-hint">[]<br></li></ul>`,
                stepFunction: toggleUnorderedList,
                contentAfterEdit: `<p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`,
                contentAfter: "<p>[]<br></p>",
            });
        });

        test("should turn a list into a paragraph", async () => {
            await testEditor({
                contentBefore: "<ul><li>ab[]cd</li></ul>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<p>ab[]cd</p>",
            });
        });

        test("should turn a list into a heading", async () => {
            await testEditor({
                contentBefore: "<ul><li><h1>ab[]cd</h1></li></ul>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<h1>ab[]cd</h1>",
            });
        });

        test("should turn a list item into a paragraph", async () => {
            await testEditor({
                contentBefore: "<p>ab</p><ul><li>cd</li><li>ef[]gh</li></ul>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<p>ab</p><ul><li>cd</li></ul><p>ef[]gh</p>",
            });
        });

        test("should turn a list with formats into a paragraph", async () => {
            await testEditor({
                contentBefore:
                    "<ul><li><span><b>ab</b></span> <span><i>cd</i></span> ef[]gh</li></ul>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<p><span><b>ab</b></span> <span><i>cd</i></span> ef[]gh</p>",
            });
        });

        test("should turn nested list items into paragraphs", async () => {
            await testEditor({
                contentBefore: unformat(`
                        <ul>
                            <li><p>a</p>
                                <ul>
                                    <li><p>[]b</p>
                                        <ul>
                                            <li>c</li>
                                        </ul>
                                    </li>
                                </ul>
                            </li>
                        </ul>`),
                stepFunction: toggleUnorderedList,
                contentAfter: unformat(`
                        <ul>
                            <li><p>a</p></li>
                        </ul>
                        <p>[]b</p>
                        <ul>
                            <li class="oe-nested">
                                <ul>
                                    <li class="oe-nested">
                                        <ul>
                                            <li>c</li>
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
                                <td>[<ul><li><br></li></ul></td>
                                <td><ul><li><br></li></ul></td>
                                <td><ul><li><br></li></ul></td>
                            </tr>
                            <tr>
                                <td><ul><li><br></li></ul></td>
                                <td><ul><li><br></li></ul></td>
                                <td><ul><li><br></li></ul>]</td>
                            </tr>
                        </tbody>
                    </table>
                `),
                stepFunction: toggleUnorderedList,
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
                contentBefore: "<ul><li>ab<br>cd<br>ef[]</li></ul>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<p>ab<br>cd<br>ef[]</p>",
            });
        });

        test("should convert list item with line breaks into a single paragraph (2)", async () => {
            await testEditor({
                contentBefore: "<ul><li>ab<br><b>cd</b><br><i>ef[]</i></li></ul>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<p>ab<br><b>cd</b><br><i>ef[]</i></p>",
            });
        });
    });
    describe("Transform", () => {
        test("should turn an empty ordered list into an unordered list", async () => {
            await testEditor({
                contentBefore: "<ol><li>[]<br></li></ol>",
                stepFunction: toggleUnorderedList,
                contentAfterEdit: `<ul><li o-we-hint-text="List" class="o-we-hint">[]<br></li></ul>`,
                contentAfter: "<ul><li>[]<br></li></ul>",
            });
        });

        test("should turn an empty ordered list into an unordered list (2)", async () => {
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li>[]<br></li></ul>',
                stepFunction: toggleUnorderedList,
                contentAfterEdit: `<ul><li o-we-hint-text="List" class="o-we-hint">[]<br></li></ul>`,
                contentAfter: "<ul><li>[]<br></li></ul>",
            });
        });
    });
});

describe("Range not collapsed", () => {
    describe("Insert", () => {
        test("should turn a paragraph into a list", async () => {
            await testEditor({
                contentBefore: "<p>ab</p><p>cd[ef]gh</p>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<p>ab</p><ul><li>cd[ef]gh</li></ul>",
            });
        });

        test("should turn a paragraph into a list with shortcut", async () => {
            await testEditor({
                contentBefore: "<p>[abc]</p>",
                stepFunction: () => press(["control", "shift", "8"]),
                contentAfter: "<ul><li>[abc]</li></ul>",
            });
        });

        test("should turn a heading into a list", async () => {
            await testEditor({
                contentBefore: "<p>ab</p><h1>cd[ef]gh</h1>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<p>ab</p><ul><li><h1>cd[ef]gh</h1></li></ul>",
            });
        });

        test("should turn two paragraphs into a list with two items", async () => {
            await testEditor({
                contentBefore: "<p>ab</p><p>cd[ef</p><p>gh]ij</p>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<p>ab</p><ul><li>cd[ef</li><li>gh]ij</li></ul>",
            });
        });

        test("should turn two paragraphs in a div into a list with two items", async () => {
            await testEditor({
                contentBefore: "<div><p>ab[cd</p><p>ef]gh</p></div>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<div><ul><li>ab[cd</li><li>ef]gh</li></ul></div>",
            });
        });

        test("should turn a paragraph and a list item into two list items", async () => {
            await testEditor({
                contentBefore: "<p>a[b</p><ul><li>c]d</li><li>ef</li></ul>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<ul><li>a[b</li><li>c]d</li><li>ef</li></ul>",
            });
        });

        test("should turn a list item and a paragraph into two list items", async () => {
            await testEditor({
                contentBefore: "<ul><li>ab</li><li>c[d</li></ul><p>e]f</p>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<ul><li>ab</li><li>c[d</li><li>e]f</li></ul>",
            });
        });

        test("should turn a list, a paragraph and another list into one list with three list items", async () => {
            await testEditor({
                contentBefore: "<ul><li>a[b</li></ul><p>cd</p><ul><li>e]f</li></ul>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<ul><li>a[b</li><li>cd</li><li>e]f</li></ul>",
            });
        });

        test("should turn a list item, a paragraph and another list into one list with all three as list items", async () => {
            await testEditor({
                contentBefore: "<ul><li>ab</li><li>c[d</li></ul><p>ef</p><ul><li>g]h</li></ul>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<ul><li>ab</li><li>c[d</li><li>ef</li><li>g]h</li></ul>",
            });
        });

        test("should turn a list, a paragraph and a list item into one list with all three as list items", async () => {
            await testEditor({
                contentBefore: "<ul><li>a[b</li></ul><p>cd</p><ul><li>e]f</li><li>gh</li></ul>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<ul><li>a[b</li><li>cd</li><li>e]f</li><li>gh</li></ul>",
            });
        });

        test("should not turn a non-editable paragraph into a list", async () => {
            await testEditor({
                contentBefore: '<p>[ab</p><p contenteditable="false">cd</p><p>ef]</p>',
                stepFunction: toggleUnorderedList,
                contentAfter:
                    '<ul><li>[ab</li></ul><p contenteditable="false">cd</p><ul><li>ef]</li></ul>',
            });
        });

        test("should turn only the deepest blocks into lists", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <div class="container o_text_columns">
                        <div class="row">
                            <div class="col-6">
                                <p>[<br></p>
                            </div>
                            <div class="col-6">
                                <p><br>]</p>
                            </div>
                        </div>
                    </div>
                `),
                stepFunction: toggleUnorderedList,
                contentAfter: unformat(`
                    <div class="container o_text_columns">
                        <div class="row">
                            <div class="col-6">
                                <ul>
                                    <li>[<br></li>
                                </ul>
                            </div>
                            <div class="col-6">
                                <ul>
                                    <li>]<br></li>
                                </ul>
                            </div>
                        </div>
                    </div>
                `),
            });
        });

        test("should turn a list into an unordered list with text alignment", async () => {
            await testEditor({
                contentBefore:
                    '<ol><li style="text-align: center;">[abc</li><li style="text-align: center;">def]</li></ol>',
                stepFunction: toggleUnorderedList,
                contentAfter:
                    '<ul><li style="text-align: center;">[abc</li><li style="text-align: center;">def]</li></ul>',
            });
        });
        test("should apply text-align right when creating unordered list", async () => {
            await testEditor({
                contentBefore: '<p style="text-align: right;">[ab]</p>',
                stepFunction: toggleUnorderedList,
                contentAfter: '<ul><li style="text-align: right;">[ab]</li></ul>',
            });
        });
        test("should apply text-align format when creating unordered list from multiple selected blocks", async () => {
            await testEditor({
                contentBefore:
                    '<p style="text-align: right;">[ab</p><p style="text-align: center;">cd]</p>',
                stepFunction: toggleUnorderedList,
                contentAfter:
                    '<ul><li style="text-align: right;">[ab</li><li style="text-align: center;">cd]</li></ul>',
            });
        });
    });
    describe("Remove", () => {
        test("should turn a list into a paragraph", async () => {
            await testEditor({
                contentBefore: "<p>ab</p><ul><li>cd[ef]gh</li></ul>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<p>ab</p><p>cd[ef]gh</p>",
            });
        });

        test("should turn a list into a heading", async () => {
            await testEditor({
                contentBefore: "<p>ab</p><ul><li><h1>cd[ef]gh</h1></li></ul>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<p>ab</p><h1>cd[ef]gh</h1>",
            });
        });

        test("should turn a list into two paragraphs", async () => {
            await testEditor({
                contentBefore: "<p>ab</p><ul><li>cd[ef</li><li>gh]ij</li></ul>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<p>ab</p><p>cd[ef</p><p>gh]ij</p>",
            });
        });

        test("should turn a list item into a paragraph", async () => {
            await testEditor({
                contentBefore: "<p>ab</p><ul><li>cd</li><li>ef[gh]ij</li></ul>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<p>ab</p><ul><li>cd</li></ul><p>ef[gh]ij</p>",
            });
        });

        test("should not turn a non-editable list into a paragraph", async () => {
            await testEditor({
                contentBefore:
                    '<ul><li>[ab</li></ul><p contenteditable="false">cd</p><ul><li>ef]</li></ul>',
                stepFunction: toggleUnorderedList,
                contentAfter: '<p>[ab</p><p contenteditable="false">cd</p><p>ef]</p>',
            });
        });

        test("should turn an unordered list into paragraphs with text alignment", async () => {
            await testEditor({
                contentBefore:
                    '<ul><li style="text-align: center;">[abc</li><li style="text-align: right;">def]</li></ul>',
                stepFunction: toggleUnorderedList,
                contentAfter:
                    '<p style="text-align: center;">[abc</p><p style="text-align: right;">def]</p>',
            });
        });
    });
});
