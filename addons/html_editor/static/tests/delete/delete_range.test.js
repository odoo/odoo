import { describe, expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { CORE_PLUGINS } from "@html_editor/plugin_sets";
import { getContent, setSelection } from "../_helpers/selection";

async function testCoreEditor(testConfig) {
    return testEditor({ ...testConfig, config: { Plugins: CORE_PLUGINS } });
}

// Tests the deleteRange shared method.
async function deleteRange(editor) {
    // Avoid SelectionPlugin methods to avoid normalization. The goal is to
    // simulate the range passed as argument to the deleteRange method.
    const selection = editor.document.getSelection();
    let range = selection.getRangeAt(0);

    range = editor.shared.deleteRange(range);

    const { startContainer, startOffset, endContainer, endOffset } = range;
    selection.setBaseAndExtent(startContainer, startOffset, endContainer, endOffset);
}

// Tests the DELETE_SELECTION command.
async function deleteSelection(editor) {
    editor.dispatch("DELETE_SELECTION");
}

describe("deleteRange method", () => {
    describe("Basic", () => {
        test("should delete a range inside a text node in a paragraph", async () => {
            await testCoreEditor({
                contentBefore: "<p>a[bc]d</p>",
                stepFunction: deleteRange,
                contentAfterEdit: "<p>a[]d</p>",
            });
        });
        test("should delete a range across different nodes in a paragraph", async () => {
            await testCoreEditor({
                contentBefore: "<p>a[b<i>cd</i>ef<strong>gh</strong>i]j</p>",
                stepFunction: deleteRange,
                contentAfterEdit: "<p>a[]j</p>",
            });
        });
    });
    describe("Inside inline", () => {
        test("should delete a range inside an inline element", async () => {
            await testCoreEditor({
                contentBefore: "<p><strong>a[bc]d</strong></p>",
                stepFunction: deleteRange,
                contentAfterEdit: "<p><strong>a[]d</strong></p>",
            });
        });
        test("should delete a range inside an inline element and fill empty inline", async () => {
            await testCoreEditor({
                contentBefore: "<p><strong>[abcd]</strong></p>",
                stepFunction: deleteRange,
                contentAfterEdit:
                    '<p><strong data-oe-zws-empty-inline="">[]\u200b</strong><br></p>',
            });
        });
    });
    describe("Across inlines", () => {
        test("delete across two inlines (no merge)", async () => {
            await testCoreEditor({
                contentBefore: "<p><i>a[bc</i>de<i>fg]h</i></p>",
                stepFunction: deleteRange,
                contentAfterEdit: "<p><i>a[]</i><i>h</i></p>",
            });
        });
        test("delete across two inlines, start one left empty (should fill empty inline) ", async () => {
            await testCoreEditor({
                contentBefore: "<p><i>[abc</i>de<i>fg]h</i></p>",
                stepFunction: deleteRange,
                contentAfterEdit: '<p><i data-oe-zws-empty-inline="">[]\u200b</i><i>h</i></p>',
            });
        });
        test("delete across two inlines, end one left empty (should  fill empty inline) ", async () => {
            await testCoreEditor({
                contentBefore: "<p><i>a[bc</i>de<i>fgh]</i></p>",
                stepFunction: deleteRange,
                contentAfterEdit: '<p><i>a[]</i><i data-oe-zws-empty-inline="">\u200b</i></p>',
            });
        });
        test("delete across two inlines, both left empty (should fill both)", async () => {
            await testCoreEditor({
                contentBefore: "<p><i>[abc</i>de<i>fgh]</i>jkl</p>",
                stepFunction: deleteRange,
                contentAfterEdit:
                    '<p><i data-oe-zws-empty-inline="">[]\u200b</i><i data-oe-zws-empty-inline="">\u200b</i>jkl</p>',
            });
        });
        test("delete across two inlines, both left empty, block left shrunk (should fill inlines and block", async () => {
            await testCoreEditor({
                contentBefore: "<p><i>[abc</i>de<i>fgh]</i></p>",
                stepFunction: deleteRange,
                contentAfterEdit:
                    '<p><i data-oe-zws-empty-inline="">[]\u200b</i><i data-oe-zws-empty-inline="">\u200b</i><br></p>',
            });
        });
    });
    describe("Inside block", () => {
        test("should delete a range inside a text node in a paragraph and fill shrunk block", async () => {
            await testCoreEditor({
                contentBefore: "<p>[abcd]</p>",
                stepFunction: deleteRange,
                contentAfterEdit: "<p>[]<br></p>",
            });
        });
    });
    describe("Across blocks", () => {
        test("should merge paragraphs", async () => {
            await testEditor({
                contentBefore: "<p>ab[c</p><p>d]ef</p>",
                stepFunction: deleteRange,
                contentAfter: "<p>ab[]ef</p>",
            });
        });

        test("should merge right block's content into left block", async () => {
            await testEditor({
                contentBefore: "<h1>ab[c</h1><p>d]ef</p>",
                stepFunction: deleteRange,
                contentAfter: "<h1>ab[]ef</h1>",
            });
        });

        test("should merge right block's content into fully selected left block", async () => {
            // As opposed to the DELETE_SELECTION command, in which fully selected block on the left is removed.
            // See "should remove fully selected left block and keep second block"
            await testEditor({
                contentBefore: "<h1>[abc</h1><p>d]ef</p>",
                stepFunction: deleteRange,
                contentAfter: "<h1>[]ef</h1>",
            });
        });

        test("should merge right block's content into left block and fill shrunk block", async () => {
            await testEditor({
                contentBefore: "<h1>[abc</h1><p>def]</p>",
                stepFunction: deleteRange,
                contentAfter: "<h1>[]<br></h1>",
            });
        });
        test("should not merge paragraph with paragraph before it", async () => {
            await testEditor({
                contentBefore: "<div><p>abc</p>[<p>]def</p></div>",
                stepFunction: deleteRange,
                contentAfter: "<div><p>abc</p>[]<p>def</p></div>",
            });
        });
        test("should merge paragraph with paragraph before it", async () => {
            await testEditor({
                contentBefore: "<div><p>abc[</p><p>]def</p></div>",
                stepFunction: deleteRange,
                contentAfter: "<div><p>abc[]def</p></div>",
            });
        });
    });
    describe("Block + inline", () => {
        test("should merge paragraph with inline content after it", async () => {
            await testEditor({
                contentBefore: "<div><p>ab[c</p>d]ef</div>",
                stepFunction: deleteRange,
                contentAfter: "<div><p>ab[]ef</p></div>",
            });
        });

        test("should merge paragraph with inline content after it (2)", async () => {
            // This is the kind of range passed to deleteRange on `...</p>[]def...` + deleteBackward
            await testEditor({
                contentBefore: "<div><p>abc[</p>]def</div>",
                stepFunction: deleteRange,
                contentAfter: "<div><p>abc[]def</p></div>",
            });
        });
    });
    describe("Inline + block", () => {
        test("should merge paragraph with inline content before it (remove paragraph)", async () => {
            await testEditor({
                contentBefore: "<div>ab[c<p>d]ef</p></div>",
                stepFunction: deleteRange,
                contentAfter: "<div>ab[]ef</div>",
            });
        });

        test("should merge paragraph with inline content before it", async () => {
            await testEditor({
                contentBefore: "<div>ab[c<p>d]ef</p><p>ghi</p></div>",
                stepFunction: deleteRange,
                contentAfter: "<div>ab[]ef<p>ghi</p></div>",
            });
        });

        test("should merge paragraph with inline content before it (remove paragraph) (2)", async () => {
            await testEditor({
                contentBefore: "<div>abc[<p>]def</p></div>",
                stepFunction: deleteRange,
                contentAfter: "<div>abc[]def</div>",
            });
        });

        test("should merge paragraph with inline content before it and insert a line-break after it", async () => {
            await testEditor({
                contentBefore: "<div>ab[c<p>d]ef</p>ghi</div>",
                stepFunction: deleteRange,
                contentAfter: "<div>ab[]ef<br>ghi</div>",
            });
        });

        test("should merge nested paragraph with inline content before it and insert a line-break after it", async () => {
            await testEditor({
                contentBefore: `<div>ab[c<custom-block style="display: block;"><p>d]ef</p></custom-block>ghi</div>`,
                stepFunction: deleteRange,
                contentAfter: "<div>ab[]ef<br>ghi</div>",
            });
        });
    });
    describe("Fake line breaks", () => {
        test("should not crash if cursor is inside a fake BR", async () => {
            // The goal of this tests is to make sure deleteRange does not rely
            // on selection normaliztion.  It should not assume that the cursor
            // is never inside a BR.
            const contentBefore = unformat(
                `<table><tbody>
                    <tr><td><br></td><td><br></td></tr>
                    <tr><td><br></td><td><br></td></tr>
                </tbody></table>`
            );
            const { editor, el } = await setupEditor(contentBefore);
            // Place the cursor inside the BR.
            setSelection({
                anchorNode: el,
                anchorOffset: 0,
                focusNode: el.querySelector("tr:nth-child(2) td br"),
                focusOffset: 0,
            });
            /* [<table><tbody>
                    <tr><td><br></td><td><br></td></tr>
                    <tr><td><]br></td><td><br></td></tr>
                </tbody></table>
            */
            deleteRange(editor);
            const contentAfter = unformat(
                `[<table><tbody>
                    <tr><td><br></td><td><br></td></tr>
                    <tr><td>]<br></td><td><br></td></tr>
                </tbody></table>`
            );
            expect(getContent(el)).toBe(contentAfter);
        });
    });
    describe("Fill shrunk blocks", () => {
        test("should not fill a HR with BR", async () => {
            const { editor, el } = await setupEditor("<hr><p>abc[</p><p>]def</p>");
            deleteRange(editor);
            const hr = el.firstElementChild;
            expect(hr.childNodes.length).toBe(0);
        });
    });
});

describe("DELETE_SELECTION command", () => {
    describe("Merge blocks", () => {
        test("should remove fully selected left block and keep second block", async () => {
            // As opposed to the deleteRange method.
            // This is done by expanding the range to fully include the left
            // block before calling deleteRange. See `includeEndOrStartBlock` method.
            // <h1>[abc</h1><p>d]ef</p> -> [<h1>abc</h1><p>d]ef</p> -> deleteRange
            await testEditor({
                contentBefore: "<h1>[abc</h1><p>d]ef</p>",
                stepFunction: deleteSelection,
                contentAfter: "<p>[]ef</p>",
            });
        });

        test("should keep left block if both have been emptied", async () => {
            await testEditor({
                contentBefore: "<h1>[abc</h1><p>def]</p>",
                stepFunction: deleteSelection,
                contentAfter: "<h1>[]<br></h1>",
            });
        });
    });

    describe("Unmergeables", () => {
        test("should not merge paragraph with unmeargeble block", async () => {
            await testEditor({
                contentBefore: "<p>ab[c</p><div>d]ef</div>",
                stepFunction: deleteSelection,
                contentAfter: "<p>ab[]</p><div>ef</div>",
            });
        });

        test("should remove unmergeable block that has been emptied", async () => {
            // `includeEndOrStartBlock` fully includes the right block.
            // <p>ab[c</p><div>def]</div> -> <p>ab[c</p><div>def</div>] -> deleteRange
            await testEditor({
                contentBefore: "<p>ab[c</p><div>def]</div>",
                stepFunction: deleteSelection,
                contentAfter: "<p>ab[]</p>",
            });
        });
    });

    describe("Unremovables", () => {
        test("should not remove unremovable node, but clear its content", async () => {
            await testEditor({
                contentBefore: `<p>a[bc</p><div class="oe_unremovable">def</div><p>gh]i</p>`,
                stepFunction: deleteSelection,
                contentAfter: `<p>a[]</p><div class="oe_unremovable"><br></div><p>i</p>`,
            });
        });
        test("should move the unremovable up the tree", async () => {
            await testEditor({
                contentBefore: `<p>a[bc</p><div><div class="oe_unremovable">def</div></div><p>gh]i</p>`,
                stepFunction: deleteSelection,
                contentAfter: `<p>a[]</p><div class="oe_unremovable"><br></div><p>i</p>`,
            });
        });
        test("should preserve parent-child relations between unremovables", async () => {
            await testEditor({
                contentBefore: unformat(
                    `<p>a[bc</p>
                    <div>
                        <div class="oe_unremovable">
                            <div class="oe_unremovable">jkl</div>
                            <p>mno</p>
                        </div>
                    </div>
                    <p>gh]i</p>`
                ),
                stepFunction: deleteSelection,
                contentAfter: unformat(
                    `<p>a[]</p>
                    <div class="oe_unremovable">
                        <div class="oe_unremovable"><br></div>
                    </div>
                    <p>i</p>`
                ),
            });
        });
        test("should preserve parent-child relations between unremovables (2)", async () => {
            await testEditor({
                contentBefore: unformat(
                    `<p>a[bc</p>
                    <div class="oe_unremovable">xyz</div>
                    <div>
                        <div class="oe_unremovable">
                            <div>
                                <div class="oe_unremovable">jkl</div>
                            </div>
                            <p>mno</p>
                            <div class="oe_unremovable">mno</div>
                        </div>
                    </div>
                    <p>gh]i</p>`
                ),
                stepFunction: deleteSelection,
                contentAfter: unformat(
                    `<p>a[]</p>
                    <div class="oe_unremovable"><br></div>
                    <div class="oe_unremovable">
                        <div class="oe_unremovable"><br></div>
                        <div class="oe_unremovable"><br></div>
                    </div>
                    <p>i</p>`
                ),
            });
        });
    });

    describe("Conditional unremovables", () => {
        describe("Bootstrap columns", () => {
            test("should not remove bootstrap columns, but clear its content", async () => {
                await testEditor({
                    contentBefore: unformat(
                        `<div class="container o_text_columns">
                            <div class="row">
                                <div class="col-6">a[bc</div>
                                <div class="col-6">def</div>
                            </div>
                        </div>
                        <p>gh]i</p>`
                    ),
                    stepFunction: deleteSelection,
                    contentAfterEdit: unformat(
                        `<div class="container o_text_columns">
                            <div class="row">
                                <div class="col-6">a[]</div>
                                <div class="col-6"><br></div>
                            </div>
                        </div>
                        <p>i</p>`
                    ),
                    contentAfter: unformat(
                        `<div class="container o_text_columns">
                            <div class="row">
                                <div class="col-6">a[]</div>
                                <div class="col-6"><br></div>
                            </div>
                        </div>
                        <p>i</p>`
                    ),
                });
            });
            test("should remove bootstrap columns", async () => {
                await testEditor({
                    contentBefore: unformat(
                        `<p>x[yz</p>
                        <div class="container o_text_columns">
                            <div class="row">
                                <div class="col-6">abc</div>
                                <div class="col-6">def</div>
                            </div>
                        </div>
                        <p>gh]i</p>`
                    ),
                    stepFunction: deleteSelection,
                    contentAfter: "<p>x[]i</p>",
                });
            });
        });
        describe("Table cells", () => {
            test("should not remove table cell, but clear its content", async () => {
                // Actually this is handled by the table plugin, and does not
                // involve the unremovable mechanism.
                await testEditor({
                    contentBefore: unformat(
                        `<table><tbody>
                            <tr>
                                <td>[a</td> <td>b]</td> <td>c</td> 
                            </tr>
                            <tr>
                                <td>d</td> <td>e</td> <td>f</td> 
                            </tr>
                        </tbody></table>`
                    ),
                    stepFunction: deleteSelection,
                    contentAfter: unformat(
                        `<table><tbody>
                            <tr>
                                <td>[]<br></td> <td><br></td> <td>c</td> 
                            </tr>
                            <tr>
                                <td>d</td> <td>e</td> <td>f</td> 
                            </tr>
                        </tbody></table>`
                    ),
                });
            });
            test("should remove table", async () => {
                await testEditor({
                    contentBefore: unformat(
                        `<p>a[bc</p>
                        <table><tbody>
                            <tr>
                                <td><p>abc</p></td><td><p>def</p></td>
                            </tr>
                        </tbody></table>
                        <p>gh]i</p>`
                    ),
                    stepFunction: deleteSelection,
                    contentAfter: "<p>a[]i</p>",
                });
            });
        });
    });
    describe("Allowed content mismatch on blocks merge", () => {
        test("should not add H1 (flow content) to P (allows phrasing content only)", async () => {
            await testEditor({
                contentBefore: unformat(
                    `<p>a[bc</p>
                    <ul>
                        <li>
                            <h1>def</h1>]
                            <h1>ghi</h1>
                        </li>
                    </ul>`
                ),
                stepFunction: deleteSelection,
                contentAfter: unformat(
                    `<p>a[]</p>
                    <ul>
                        <li>
                            <h1>ghi</h1>
                        </li>
                    </ul>`
                ),
            });
        });
        test("should add P (flow content) to LI (allows flow content) ", async () => {
            await testEditor({
                contentBefore: unformat(
                    `<ul>
                        <li>
                            <h1>abc</h1>
                            [<h1>def</h1>
                        </li>
                        <li>
                            <p>ghi</p>]
                            <p>jkl</p>
                        </li>
                    </ul>`
                ),
                stepFunction: deleteSelection,
                contentAfter: unformat(
                    `<ul>
                        <li>
                            <h1>abc</h1>
                            <p>[]jkl</p>
                        </li>
                    </ul>`
                ),
            });
        });
    });
});
