import { describe, expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { splitBlock, keydownTab, undo, tripleClick } from "../_helpers/user_actions";
import { getContent } from "../_helpers/selection";

describe("Checklist", () => {
    test("should indent a checklist (1)", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li class="o_checked">a[b]c</li>
                    </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">a[b]c</li>
                            </ul>
                        </li>
                    </ul>`),
        });
    });

    test("should indent a checklist (2)", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li>a[b]c</li>
                    </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li>a[b]c</li>
                            </ul>
                        </li>
                    </ul>`),
        });
    });

    test('should indent a checklist and previous line become the "title" (1)', async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li class="o_checked">abc</li>
                        <li class="o_checked">d[e]f</li>
                    </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li class="o_checked">abc</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                            <li class="o_checked">d[e]f</li>
                            </ul>
                        </li>
                    </ul>`),
        });
    });

    test('should indent a checklist and previous line become the "title" (2)', async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li class="o_checked">abc</li>
                        <li>d[e]f</li>
                    </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li class="o_checked">abc</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li>d[e]f</li>
                            </ul>
                        </li>
                    </ul>`),
        });
    });

    test('should indent a checklist and previous line become the "title" (3)', async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li>abc</li>
                        <li>d[e]f</li>
                    </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li>abc</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                            <li>d[e]f</li>
                            </ul>
                        </li>
                    </ul>`),
        });
    });

    test('should indent a checklist and previous line become the "title" (4)', async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li>abc</li>
                        <li class="o_checked">d[e]f</li>
                    </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li>abc</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                            <li class="o_checked">d[e]f</li>
                            </ul>
                        </li>
                    </ul>`),
        });
    });

    test("should indent a checklist and merge it with previous siblings (1)", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">def</li>
                            </ul>
                        </li>
                        <li class="o_checked">g[h]i</li>
                    </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">def</li>
                                <li class="o_checked">g[h]i</li>
                            </ul>
                        </li>
                    </ul>`),
        });
    });

    test("should indent a checklist and merge it with previous siblings (2)", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li>abc</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li>def</li>
                            </ul>
                        </li>
                        <li class="o_checked">g[h]i</li>
                    </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li>abc</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li>def</li>
                                <li class="o_checked">g[h]i</li>
                            </ul>
                        </li>
                    </ul>`),
        });
    });

    test("should indent a checklist and merge it with previous siblings (3)", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li class="o_checked">abc</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">def</li>
                            </ul>
                        </li>
                        <li>g[h]i</li>
                    </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li class="o_checked">abc</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">def</li>
                                <li>g[h]i</li>
                            </ul>
                        </li>
                    </ul>`),
        });
    });

    test("should indent a checklist and merge it with next siblings (1)", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li class="o_checked">abc</li>
                        <li class="o_checked">d[e]f</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">ghi</li>
                            </ul>
                        </li>
                    </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li class="o_checked">abc</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">d[e]f</li>
                                <li class="o_checked">ghi</li>
                            </ul>
                        </li>
                    </ul>`),
        });
    });

    test("should indent a checklist and merge it with next siblings (2)", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li>abc</li>
                        <li class="o_checked">d[e]f</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">ghi</li>
                            </ul>
                        </li>
                    </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li>abc</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">d[e]f</li>
                                <li class="o_checked">ghi</li>
                            </ul>
                        </li>
                    </ul>`),
        });
    });

    test("should indent a checklist and merge it with next siblings (3)", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li class="o_checked">abc</li>
                        <li>d[e]f</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li>ghi</li>
                            </ul>
                        </li>
                    </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li class="o_checked">abc</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li>d[e]f</li>
                                <li>ghi</li>
                            </ul>
                        </li>
                    </ul>`),
        });
    });
});

describe("Regular list", () => {
    test("should indent a regular list empty item", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul>
                        <li>abc</li>
                        <li>[]</li>
                    </ul>
                    <p>def</p>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                    <ul>
                        <li>abc</li>
                        <li class="oe-nested">
                            <ul>
                                <li>[]</li>
                            </ul>
                        </li>
                    </ul>
                    <p>def</p>`),
        });
    });

    test("should indent a regular list empty item after an splitBlock", async () => {
        await testEditor({
            contentBefore: unformat(`
                    <ul>
                        <li>abc[]</li>
                    </ul>
                    <p>def</p>`),
            stepFunction: async (editor) => {
                splitBlock(editor);
                await keydownTab(editor);
            },
            contentAfter: unformat(`
                    <ul>
                        <li>abc</li>
                        <li class="oe-nested">
                            <ul>
                                <li>[]<br></li>
                            </ul>
                        </li>
                    </ul>
                    <p>def</p>`),
        });
    });
    test("indent regular list item when selection is not within unspittable block element", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li><br></li>
                    <li>
                        <br>[]
                        <table>
                            <tbody>
                                <tr>
                                    <td>ab</td>
                                    <td>cd</td>
                                    <td>ef</td>
                                </tr>
                            </tbody>
                        </table>
                        <br>
                    </li>
                </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                <ul>
                    <li><br></li>
                    <li class="oe-nested">
                        <ul>
                            <li>
                                []<br>
                                <table>
                                    <tbody>
                                        <tr>
                                            <td>ab</td>
                                            <td>cd</td>
                                            <td>ef</td>
                                        </tr>
                                    </tbody>
                                </table>
                                <br>
                            </li>
                        </ul>
                    </li>
                </ul>`),
        });
    });
});

describe("with selection collapsed", () => {
    test("should indent the first element of a list", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>a[]</li>
                    <li>b</li>
                </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                <ul>
                    <li class="oe-nested">
                        <ul>
                            <li>a[]</li>
                        </ul>
                    </li>
                    <li>b</li>
                </ul>`),
        });
    });

    test("should indent the last element of a list", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>a</li>
                    <li>[]b</li>
                </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li>[]b</li>
                        </ul>
                    </li>
                </ul>`),
        });
    });

    test("should indent multi-level", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>
                        a
                        <ul>
                            <li>[]b</li>
                        </ul>
                    </li>
                </ul>`),
            contentBeforeEdit: unformat(`
                <ul>
                    <li>
                        <p>a</p>
                        <ul>
                            <li>[]b</li>
                        </ul>
                    </li>
                </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                <ul>
                    <li>
                        <p>a</p>
                        <ul>
                            <li class="oe-nested">
                                <ul>
                                    <li>[]b</li>
                                </ul>
                            </li>
                        </ul>
                    </li>
                </ul>`),
        });
    });

    test("should indent the last element of a list with proper with unordered list", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ol>
                    <li>a</li>
                    <li>[]b</li>
                </ol>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                <ol>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ol>
                            <li>[]b</li>
                        </ol>
                    </li>
                </ol>`),
        });
    });

    test("should indent the middle element of a list", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>a</li>
                    <li>[]b</li>
                    <li>c</li>
                </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li>[]b</li>
                        </ul>
                    </li>
                    <li>
                        c
                    </li>
                </ul>`),
        });
    });

    test("should indent even if the first element of a list is selected", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>[]a</li>
                    <li>b</li>
                </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                <ul>
                    <li class="oe-nested">
                        <ul>
                            <li>[]a</li>
                        </ul>
                    </li>
                    <li>b</li>
                </ul>`),
        });
    });

    test("should indent only one element of a list with sublist", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>a</li>
                    <li>
                        []b
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li>c</li>
                        </ul>
                    </li>
                </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li>[]b</li>
                            <li>c</li>
                        </ul>
                    </li>
                </ul>`),
        });
    });

    test("should convert mixed lists", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>a</li>
                    <li>
                        []b
                    </li>
                    <li class="oe-nested">
                        <ol>
                            <li>c</li>
                        </ol>
                    </li>
                </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ol>
                            <li>[]b</li>
                            <li>c</li>
                        </ol>
                    </li>
                </ul>`),
        });
    });

    test("should rejoin after indent", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ol>
                    <li class="oe-nested">
                        <ol>
                            <li>a</li>
                        </ol>
                    </li>
                    <li>
                        []b
                    </li>
                    <li class="oe-nested">
                        <ol>
                            <li>c</li>
                        </ol>
                    </li>
                </ol>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                <ol>
                    <li class="oe-nested">
                        <ol>
                            <li>a</li>
                            <li>[]b</li>
                            <li>c</li>
                        </ol>
                    </li>
                </ol>`),
        });
    });

    test("should indent unordered list inside a table cell", async () => {
        await testEditor({
            contentBefore: unformat(`
                        <table>
                            <tbody>
                                <tr>
                                    <td>
                                        <ul>
                                            <li>abc</li>
                                            <li>def[]</li>
                                        </ul>
                                    </td>
                                    <td>
                                        ghi
                                    </td>
                                    <td>
                                        jkl
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    `),
            stepFunction: async (editor) => await keydownTab(editor),
            contentAfter: unformat(`
                        <table>
                            <tbody>
                                <tr>
                                    <td>
                                        <ul>
                                            <li>abc</li>
                                            <li class="oe-nested">
                                                <ul>
                                                    <li>def[]</li>
                                                </ul>
                                            </li>
                                        </ul>
                                    </td>
                                    <td>
                                        ghi
                                    </td>
                                    <td>
                                        jkl
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    `),
        });
    });

    test("should indent checklist inside a table cell", async () => {
        await testEditor({
            contentBefore: unformat(`
                        <table>
                            <tbody>
                                <tr>
                                    <td>
                                        <ul class="o_checklist">
                                            <li>abc</li>
                                            <li>def[]</li>
                                        </ul>
                                    </td>
                                    <td>
                                        ghi
                                    </td>
                                    <td>
                                        jkl
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    `),
            stepFunction: async (editor) => await keydownTab(editor),
            contentAfter: unformat(`
                        <table>
                            <tbody>
                                <tr>
                                    <td>
                                        <ul class="o_checklist">
                                            <li>abc</li>
                                            <li class="oe-nested">
                                                <ul class="o_checklist">
                                                    <li>def[]</li>
                                                </ul>
                                            </li>
                                        </ul>
                                    </td>
                                    <td>
                                        ghi
                                    </td>
                                    <td>
                                        jkl
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    `),
        });
    });

    test("should not indent a nav-item list", async () => {
        await testEditor({
            contentBefore: '<ul><li class="nav-item">a[]</li></ul>',
            stepFunction: keydownTab,
            contentAfter: '<ul><li class="nav-item">a[]</li></ul>',
        });
    });
});

describe("with selection", () => {
    test("should indent the first element of a list", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>[a]</li>
                    <li>b</li>
                </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                <ul>
                    <li class="oe-nested">
                        <ul>
                            <li>[a]</li>
                        </ul>
                    </li>
                    <li>b</li>
                </ul>`),
        });
    });

    test("should indent the middle element of a list", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>a</li>
                    <li>[b]</li>
                    <li>c</li>
                </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li>[b]</li>
                        </ul>
                    </li>
                    <li>
                        c
                    </li>
                </ul>`),
        });
    });

    test("should indent list item containing a block", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>
                        <h1>[abc]</h1>
                    </li>
                </ul>
            `),
            stepFunction: async (editor) => await keydownTab(editor),
            contentAfter: unformat(`
                <ul>
                    <li class="oe-nested">
                        <ul>
                            <li>
                                <h1>[abc]</h1>
                            </li>
                        </ul>
                    </li>
                </ul>
            `),
        });
    });

    test("should indent list item containing a block (2)", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    [<li><h1>abc</h1></li>]
                </ul>
            `),
            stepFunction: async (editor) => await keydownTab(editor),
            contentAfter: unformat(`
                <ul>
                    <li class="oe-nested">
                        <ul>
                            [<li><h1>abc</h1></li>]
                        </ul>
                    </li>
                </ul>
            `),
        });
    });

    test("should indent three list items, one of them containing a block", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>[a</li>
                    <li><h1>b</h1></li>
                    <li>c]</li>
                </ul>
            `),
            stepFunction: async (editor) => await keydownTab(editor),
            contentAfter: unformat(`
                <ul>
                    <li class="oe-nested">
                        <ul>
                            <li>[a</li>
                            <li>
                                <h1>b</h1>
                            </li>
                            <li>c]</li>
                        </ul>
                    </li>
                </ul>
            `),
        });
    });

    test("should indent multi-level (1)", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li>[b]</li>
                        </ul>
                    </li>
                </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li class="oe-nested">
                                <ul>
                                    <li>[b]</li>
                                </ul>
                            </li>
                        </ul>
                    </li>
                </ul>`),
        });
    });

    test("should indent multi-level (2)", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li class="oe-nested">
                                <ul>
                                    <li>[b]</li>
                                </ul>
                            </li>
                        </ul>
                    </li>
                </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li class="oe-nested">
                                <ul>
                                    <li class="oe-nested">
                                        <ul>
                                            <li>[b]</li>
                                        </ul>
                                    </li>
                                </ul>
                            </li>
                        </ul>
                    </li>
                </ul>`),
        });
    });

    test("should indent two multi-levels (1)", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li>[b</li>
                            <li class="oe-nested">
                                <ul>
                                    <li>c]</li>
                                </ul>
                            </li>
                        </ul>
                    </li>
                </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li class="oe-nested">
                                <ul>
                                    <li>[b</li>
                                    <li class="oe-nested">
                                        <ul>
                                            <li>c]</li>
                                        </ul>
                                    </li>
                                </ul>
                            </li>
                        </ul>
                    </li>
                </ul>`),
        });
    });

    test("should indent two multi-levels (2)", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li class="oe-nested">
                                <ul>
                                    <li>[b
                                    </li><li class="oe-nested">
                                        <ul>
                                            <li>c]</li>
                                        </ul>
                                    </li>
                                </ul>
                            </li>
                        </ul>
                    </li>
                </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li class="oe-nested">
                                <ul>
                                    <li class="oe-nested">
                                        <ul>
                                            <li>[b</li>
                                            <li class="oe-nested">
                                                <ul>
                                                    <li>c]</li>
                                                </ul>
                                            </li>
                                        </ul>
                                    </li>
                                </ul>
                            </li>
                        </ul>
                    </li>
                </ul>`),
        });
    });

    test("should indent multiples list item in the middle element of a list", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>a</li>
                    <li>[b</li>
                    <li>c]</li>
                    <li>d</li>
                </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li>[b</li>
                            <li>c]</li>
                        </ul>
                    </li>
                    <li>
                        d
                    </li>
                </ul>`),
        });
    });

    test("should indent multiples list item with reversed range", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>a</li>
                    <li>]b</li>
                    <li>c[</li>
                    <li>d</li>
                </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li>]b</li>
                            <li>c[</li>
                        </ul>
                    </li>
                    <li>
                        d
                    </li>
                </ul>`),
        });
    });

    test("should indent multiples list item in the middle element of a list with sublist", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>a</li>
                    <li>
                        [b
                    </li><li class="oe-nested">
                        <ul>
                            <li>c</li>
                        </ul>
                    </li>
                    <li>d]</li>
                    <li>e</li>
                </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li>
                                [b
                            </li>
                            <li class="oe-nested">
                                <ul>
                                    <li>c</li>
                                </ul>
                            </li>
                            <li>d]</li>
                        </ul>
                    </li>
                    <li>e</li>
                </ul>`),
        });
    });

    test("should indent with mixed lists", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>a</li>
                    <li>
                        [b
                    </li><li class="oe-nested">
                        <ol>
                            <li>c]</li>
                        </ol>
                    </li>
                </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ol>
                            <li>
                                [b
                            </li>
                            <li class="oe-nested">
                                <ol>
                                    <li>c]</li>
                                </ol>
                            </li>
                        </ol>
                    </li>
                </ul>`),
        });
    });

    test("should only indent elements with selected content (mix lists)", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>a</li>
                    <li>
                        [b
                    </li><li class="oe-nested">
                        <ol>
                            <li>]c</li>
                        </ol>
                    </li>
                </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                <ul>
                    <li>a</li>
                    <li class="oe-nested">
                        <ol>
                            <li>[b</li>
                            <li class="oe-nested">
                                <ol>
                                    <li>]c</li>
                                </ol>
                            </li>
                        </ol>
                    </li>
                </ul>`),
        });
    });

    test("should only indent elements with selected content (mix lists - triple click)", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>a</li>
                    <li>
                        [b
                    </li><li class="oe-nested">
                        <ol>
                            <li>]c</li>
                        </ol>
                    </li>
                </ul>`),
            stepFunction: async (editor) => {
                await tripleClick(editor.editable.querySelectorAll("li")[1]);
                await keydownTab(editor);
            },
            contentAfter: unformat(`
                <ul>
                    <li>a</li>
                    <li class="oe-nested">
                        <ol>
                            <li>[b]</li>
                            <li>c</li>
                        </ol>
                    </li>
                </ul>`),
        });
    });

    test("should indent nested list and list with elements in a upper level than the rangestart", async () => {
        await testEditor({
            contentBefore: unformat(`
                <ul>
                    <li>a</li>
                    <li>
                        b
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li>c</li>
                            <li>[d</li>
                        </ul>
                    </li>
                    <li>
                        e
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li>f</li>
                            <li>g</li>
                        </ul>
                    </li>
                    <li>h]</li>
                    <li>i</li>
                </ul>`),
            stepFunction: keydownTab,
            contentAfter: unformat(`
                <ul>
                    <li>a</li>
                    <li>
                        b
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li>
                                c
                            </li>
                            <li class="oe-nested">
                                <ul>
                                    <li>[d</li>
                                </ul>
                            </li>
                            <li>
                            e
                            </li>
                            <li class="oe-nested">
                            <ul>
                                <li>f</li>
                                <li>g</li>
                            </ul>
                        </li>
                        <li>h]</li>
                        </ul>
                    </li>
                    <li>i</li>
                </ul>`),
        });
    });

    test("should not indent a non-editable list", async () => {
        const tab = '<span class="oe-tabs" style="width: 40px;">\u0009</span>\u200B';
        await testEditor({
            contentBefore: unformat(`
                <p>[before</p>
                <ul>
                    <li>a</li>
                </ul>
                <ul contenteditable="false">
                    <li>a</li>
                </ul>
                <p>after]</p>`),
            stepFunction: keydownTab,
            contentAfter:
                `<p>${tab}[before</p>` +
                unformat(`
                    <ul>
                        <li class="oe-nested">
                            <ul>
                                <li>a</li>
                            </ul>
                        </li>
                    </ul>
                    <ul contenteditable="false">
                        <li>a</li>
                    </ul>`) +
                `<p>${tab}after]</p>`,
        });
    });

    test("should indent ordered list inside a table cell", async () => {
        await testEditor({
            contentBefore: unformat(`
                        <table>
                            <tbody>
                                <tr>
                                    <td>
                                        <ol>
                                            <li>abc</li>
                                            <li>[def]</li>
                                        </ol>
                                    </td>
                                    <td>
                                        ghi
                                    </td>
                                    <td>
                                        jkl
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    `),
            stepFunction: async (editor) => await keydownTab(editor),
            contentAfter: unformat(`
                        <table>
                            <tbody>
                                <tr>
                                    <td>
                                        <ol>
                                            <li>abc</li>
                                            <li class="oe-nested">
                                                <ol>
                                                    <li>[def]</li>
                                                </ol>
                                            </li>
                                        </ol>
                                    </td>
                                    <td>
                                        ghi
                                    </td>
                                    <td>
                                        jkl
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    `),
        });
    });
});

describe("Mixed: list + paragraph", () => {
    test("should indent a list and paragraph", async () => {
        const contentBefore = unformat(`
            <ul>
                <li>[abc</li>
            </ul>
            <p>def]</p>`);
        const { el, editor } = await setupEditor(contentBefore);

        await keydownTab(editor);

        /* eslint-disable */
        const expectedContent =
            unformat(`
            <ul>
                <li class="oe-nested">
                    <ul>
                        <li>[abc</li>
                    </ul>
                </li>
            </ul>`) +
            '<p><span class="oe-tabs" contenteditable="false" style="width: 40px;">\t</span>\u200bdef]</p>';
        /* eslint-enable */
        expect(getContent(el)).toBe(expectedContent);

        // Check that it was done as single history step.
        undo(editor);
        expect(getContent(el)).toBe(contentBefore);
    });
});
