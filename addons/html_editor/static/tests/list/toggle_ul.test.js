import { describe, test } from "@odoo/hoot";
import { testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { toggleUnorderedList } from "../_helpers/user_actions";

describe("Range collapsed", () => {
    describe("Insert", () => {
        test("should turn an empty paragraph into a list", async () => {
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                contentBeforeEdit: `<p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>`,
                stepFunction: toggleUnorderedList,
                contentAfterEdit: `<ul><li placeholder="List" class="o-we-hint">[]<br></li></ul>`,
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

        test("should turn a first line into a list", async () => {
            await testEditor({
                contentBefore: "<p>a[]<br>b<br>c<br>d<br>e</p>",
                stepFunction: toggleUnorderedList,
                contentAfter: '<ul><li>a[]</li></ul><p>b<br>c<br>d<br>e</p>',
            });
        });

        test("should turn a middle line into a list", async () => {
            await testEditor({
                contentBefore: "<p>a<br>b<br>AB[]cDE<br>d<br>e</p>",
                stepFunction: toggleUnorderedList,
                contentAfter: '<p>a<br>b</p><ul><li>AB[]cDE</li></ul><p>d<br>e</p>',
            });
        });

        test("should turn a last line into a list", async () => {
            await testEditor({
                contentBefore: "<p>a<br>b<br>c<br>d<br>AB[]e</p>",
                stepFunction: toggleUnorderedList,
                contentAfter: '<p>a<br>b<br>c<br>d</p><ul><li>AB[]e</li></ul>',
            });
        });

        test("should turn an ordered list into a unordered list", async () => {
            await testEditor({
                contentBefore: "<ol><li>ab[]cd</li></ol>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<ul><li>ab[]cd</li></ul>",
            });
        });

        test("should turn an ordered list into an unordered list, with line breaks", async () => {
            await testEditor({
                contentBefore: "<ol><li>a<br>b<br>ABc[]DE<br>d<br>e</li></ol>",
                stepFunction: toggleUnorderedList,
                contentAfter: '<ul><li>a<br>b<br>ABc[]DE<br>d<br>e</li></ul>',
            });
        });

        test("should turn a checked list into a unordered list", async () => {
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li>ab[]cd</li></ul>',
                stepFunction: toggleUnorderedList,
                contentAfter: "<ul><li>ab[]cd</li></ul>",
            });
        });

        test("should turn a checked list into an unordered list, with line breaks", async () => {
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li>a<br>b<br>ABc[]DE<br>d<br>e</li></ul>',
                stepFunction: toggleUnorderedList,
                contentAfter: '<ul><li>a<br>b<br>ABc[]DE<br>d<br>e</li></ul>',
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

        test("should turn a line in a paragraph in a div into a list", async () => {
            await testEditor({
                contentBefore: "<div><p>a<br>b<br>ABc[]<br>d<br>e</p></div>",
                stepFunction: toggleUnorderedList,
                contentAfter: '<div><p>a<br>b</p><ul><li>ABc[]</li></ul><p>d<br>e</p></div>',
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

        test("should turn a line in a paragraph with formats into a list", async () => {
            await testEditor({
                contentBefore: "<p><span><b>a<br>b<br>c</b></span> <span><i>d[]<br>e</i></span> f<br>g</p>",
                stepFunction: toggleUnorderedList,
                contentAfter: '<p><span><b>a<br>b</b></span></p><ul><li><span><b>c</b></span> <span><i>d[]</i></span></li></ul><p><span><i>e</i></span> f<br>g</p>',
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
    });
    describe("Remove", () => {
        test("should turn an empty list into a paragraph", async () => {
            await testEditor({
                contentBefore: "<ul><li>[]<br></li></ul>",
                contentBeforeEdit: `<ul><li placeholder="List" class="o-we-hint">[]<br></li></ul>`,
                stepFunction: toggleUnorderedList,
                contentAfterEdit: `<p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>`,
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

        test("should turn a list into a paragraph, with line breaks", async () => {
            await testEditor({
                contentBefore: '<ul><li>a<br>b<br>[]c<br>d<br>e</li></ul>',
                stepFunction: toggleUnorderedList,
                contentAfter: "<p>a<br>b<br>[]c<br>d<br>e</p>",
            });
        });

        test("should turn a list into a heading", async () => {
            await testEditor({
                contentBefore: "<ul><li><h1>ab[]cd</h1></li></ul>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<h1>ab[]cd</h1>",
            });
        });

        test("should turn a list into a heading, with line breaks", async () => {
            await testEditor({
                contentBefore: '<ul><li><h1>a<br>b<br>[]c<br>d<br>e</h1></li></ul>',
                stepFunction: toggleUnorderedList,
                contentAfter: "<h1>a<br>b<br>[]c<br>d<br>e</h1>",
            });
        });

        test("should turn a list item into a paragraph", async () => {
            await testEditor({
                contentBefore: "<p>ab</p><ul><li>cd</li><li>ef[]gh</li></ul>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<p>ab</p><ul><li>cd</li></ul><p>ef[]gh</p>",
            });
        });

        test("should turn a list item into a paragraph, with line breaks", async () => {
            await testEditor({
                contentBefore: '<p>ab</p><ul><li>cd</li><li>e<br>f<br>[]g<br>h<br>i</li></ul>',
                stepFunction: toggleUnorderedList,
                contentAfter: '<p>ab</p><ul><li>cd</li></ul><p>e<br>f<br>[]g<br>h<br>i</p>',
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

        test("should turn a list with formats into a paragraph, with line breaks", async () => {
            await testEditor({
                contentBefore:
                    '<ul><li><span><b>ab</b></span> <span><i>cd</i></span> e<br>f<br>[]g<br>h<br>i</li></ul>',
                stepFunction: toggleUnorderedList,
                contentAfter: "<p><span><b>ab</b></span> <span><i>cd</i></span> e<br>f<br>[]g<br>h<br>i</p>",
            });
        });

        test("should turn nested list items into paragraphs", async () => {
            await testEditor({
                contentBefore: unformat(`
                        <ul>
                            <li>a</li>
                            <li class="oe-nested">
                                <ul>
                                    <li>[]b</li>
                                </ul>
                            </li>
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
                stepFunction: toggleUnorderedList,
                contentAfter: unformat(`
                        <ul>
                            <li>a</li>
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
    describe("Transform", () => {
        test("should turn an empty ordered list into an unordered list", async () => {
            await testEditor({
                contentBefore: "<ol><li>[]<br></li></ol>",
                stepFunction: toggleUnorderedList,
                contentAfterEdit: `<ul><li placeholder="List" class="o-we-hint">[]<br></li></ul>`,
                contentAfter: "<ul><li>[]<br></li></ul>",
            });
        });

        test("should turn an empty ordered list into an unordered list (2)", async () => {
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li>[]<br></li></ul>',
                stepFunction: toggleUnorderedList,
                contentAfterEdit: `<ul><li placeholder="List" class="o-we-hint">[]<br></li></ul>`,
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

        test("should turn a multi-line paragraph into a list with multiple items", async () => {
            await testEditor({
                contentBefore: "<p>[a<br>b<br>c<br>d<br>e]</p>",
                stepFunction: toggleUnorderedList,
                contentAfter: '<ul><li>[a</li><li>b</li><li>c</li><li>d</li><li>e]</li></ul>',
            });
        });

        test("should turn the first few lines of a paragraph into a list with multiple items", async () => {
            await testEditor({
                contentBefore: "<p>[a<br>b<br>c]<br>d<br>e</p>",
                stepFunction: toggleUnorderedList,
                contentAfter: '<ul><li>[a</li><li>b</li><li>c]</li></ul><p>d<br>e</p>',
            });
        });

        test("should turn the middle few lines of a paragraph into a list with multiple items", async () => {
            await testEditor({
                contentBefore: "<p>a<br>[b<br>c<br>d]<br>e</p>",
                stepFunction: toggleUnorderedList,
                contentAfter: '<p>a</p><ul><li>[b</li><li>c</li><li>d]</li></ul><p>e</p>',
            });
        });

        test("should turn a last few lines of a paragraph into a list with multiple items", async () => {
            await testEditor({
                contentBefore: "<p>a<br>b<br>[c<br>d<br>e]</p>",
                stepFunction: toggleUnorderedList,
                contentAfter: '<p>a<br>b</p><ul><li>[c</li><li>d</li><li>e]</li></ul>',
            });
        });

        test("should turn a heading into a list", async () => {
            await testEditor({
                contentBefore: "<p>ab</p><h1>cd[ef]gh</h1>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<p>ab</p><ul><li><h1>cd[ef]gh</h1></li></ul>",
            });
        });

        test("should turn a multi-line heading into a list with multiple items", async () => {
            await testEditor({
                contentBefore: "<p>xy</p><h1>AB[a<br>b<br>c<br>d<br>e]FG</h1>",
                stepFunction: toggleUnorderedList,
                contentAfter: '<p>xy</p><ul><li><h1>AB[a</h1></li><li><h1>b</h1></li><li><h1>c</h1></li><li><h1>d</h1></li><li><h1>e]FG</h1></li></ul>',
            });
        });

        test("should turn the first few lines of a heading into a list with multiple items", async () => {
            await testEditor({
                contentBefore: "<p>xy</p><h1>AB[a<br>b<br>c]<br>d<br>e</h1>",
                stepFunction: toggleUnorderedList,
                contentAfter: '<p>xy</p><ul><li><h1>AB[a</h1></li><li><h1>b</h1></li><li><h1>c]</h1></li></ul><h1>d<br>e</h1>',
            });
        });

        test("should turn the middle few lines of a heading into a list with multiple items", async () => {
            await testEditor({
                contentBefore: "<p>xy</p><h1>a<br>AB[b<br>c<br>d]EF<br>e</h1>",
                stepFunction: toggleUnorderedList,
                contentAfter: '<p>xy</p><h1>a</h1><ul><li><h1>AB[b</h1></li><li><h1>c</h1></li><li><h1>d]EF</h1></li></ul><h1>e</h1>',
            });
        });

        test("should turn a last few lines of a heading into a list with multiple items", async () => {
            await testEditor({
                contentBefore: "<p>xy</p><h1>a<br>b<br>AB[c<br>d<br>e]EF</h1>",
                stepFunction: toggleUnorderedList,
                contentAfter: '<p>xy</p><h1>a<br>b</h1><ul><li><h1>AB[c</h1></li><li><h1>d</h1></li><li><h1>e]EF</h1></li></ul>',
            });
        });

        test("should turn two paragraphs into a list with two items", async () => {
            await testEditor({
                contentBefore: "<p>ab</p><p>cd[ef</p><p>gh]ij</p>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<p>ab</p><ul><li>cd[ef</li><li>gh]ij</li></ul>",
            });
        });

        test("should turn four lines over two paragraphs into a list with four items", async () => {
            await testEditor({
                contentBefore: "<p>ab</p><p>c<br>d[e<br>f</p><p>g<br>h]i<br>j</p>",
                stepFunction: toggleUnorderedList,
                contentAfter: '<p>ab</p><p>c</p><ul><li>d[e</li><li>f</li><li>g</li><li>h]i</li></ul><p>j</p>',
            });
        });

        test("should turn two paragraphs in a div into a list with two items", async () => {
            await testEditor({
                contentBefore: "<div><p>ab[cd</p><p>ef]gh</p></div>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<div><ul><li>ab[cd</li><li>ef]gh</li></ul></div>",
            });
        });

        test("should turn four lines over two paragraphs in a div into a list with four items", async () => {
            await testEditor({
                contentBefore: "<div><p>a<br>b[c<br>d</p><p>e<br>f]g<br>h</p></div>",
                stepFunction: toggleUnorderedList,
                contentAfter:
                    '<div><p>a</p><ul><li>b[c</li><li>d</li><li>e</li><li>f]g</li></ul><p>h</p></div>',
            });
        });

        test("should turn a paragraph and a list item into two list items", async () => {
            await testEditor({
                contentBefore: "<p>a[b</p><ul><li>c]d</li><li>ef</li></ul>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<ul><li>a[b</li><li>c]d</li><li>ef</li></ul>",
            });
        });

        test("should turn two lines of a paragraph and a list item into three list items", async () => {
            await testEditor({
                contentBefore:
                    '<p>a<br>x[b<br>y</p><ul><li>c]d</li><li>ef</li></ul>',
                stepFunction: toggleUnorderedList,
                contentAfter:
                    '<p>a</p><ul><li>x[b</li><li>y</li><li>c]d</li><li>ef</li></ul>',
            });
        });

        test("should turn two lines of a paragraph and two lines of a list item into four list items", async () => {
            // TODO: is this what we want?
            await testEditor({
                contentBefore:
                    '<p>a<br>x[b<br>y</p><ul><li>c<br>z]d<br>A</li><li>ef</li></ul>',
                stepFunction: toggleUnorderedList,
                contentAfter:
                    '<p>a</p><ul><li>x[b</li><li>y</li><li>c<br>z]d<br>A</li><li>ef</li></ul>',
            });
        });

        test("should turn a list item and a paragraph into two list items", async () => {
            await testEditor({
                contentBefore: "<ul><li>ab</li><li>c[d</li></ul><p>e]f</p>",
                stepFunction: toggleUnorderedList,
                contentAfter: "<ul><li>ab</li><li>c[d</li><li>e]f</li></ul>",
            });
        });

        test("should turn a list item and two lines of a paragraph into three list items", async () => {
            await testEditor({
                contentBefore:
                    '<ul><li>ab</li><li>c[d</li></ul><p>e<br>x]f<br>g</p>',
                stepFunction: toggleUnorderedList,
                contentAfter:
                    '<ul><li>ab</li><li>c[d</li><li>e</li><li>x]f</li></ul><p>g</p>',
            });
        });

        test("should turn two lines of a list item and two lines of a paragraph into three list items", async () => {
            await testEditor({
                contentBefore:
                    '<ul><li>ab</li><li>c[d<br>A</li></ul><p>e<br>x]f<br>g</p>',
                stepFunction: toggleUnorderedList,
                contentAfter:
                    '<ul><li>ab</li><li>c[d<br>A</li><li>e</li><li>x]f</li></ul><p>g</p>',
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
    });
});
