import { test, describe } from "@odoo/hoot";
import { testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { deleteForward } from "../_helpers/user_actions";

describe("Selection collapsed", () => {
    describe("Basic", () => {
        test("should do nothing", async () => {
            await testEditor({
                contentBefore: "<ul><li>[]<br></li></ul>",
                stepFunction: deleteForward,
                contentAfter: "<ul><li>[]<br></li></ul>",
            });
            await testEditor({
                contentBefore: '<ul><li class="oe-nested"><ul><li>abc[]</li></ul></li></ul>',
                stepFunction: deleteForward,
                contentAfter: '<ul><li class="oe-nested"><ul><li>abc[]</li></ul></li></ul>',
            });
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li>[]<br></li></ul>',
                stepFunction: deleteForward,
                contentAfter: '<ul class="o_checklist"><li>[]<br></li></ul>',
            });
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">abc[]</li></ul></li></ul>',
                stepFunction: deleteForward,
                contentAfter:
                    '<ul class="o_checklist"><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">abc[]</li></ul></li></ul>',
            });
        });

        test("should delete the first character in a list item", async () => {
            await testEditor({
                contentBefore: "<ul><li>abc</li><li>[]defg</li></ul>",
                stepFunction: deleteForward,
                contentAfter: "<ul><li>abc</li><li>[]efg</li></ul>",
            });
        });

        test("should delete a character within a list item", async () => {
            await testEditor({
                contentBefore: "<ul><li>abc</li><li>de[]fg</li></ul>",
                stepFunction: deleteForward,
                contentAfter: "<ul><li>abc</li><li>de[]g</li></ul>",
            });
        });

        test("should delete the last character in a list item", async () => {
            await testEditor({
                contentBefore: "<ul><li>abc</li><li>def[]g</li></ul>",
                stepFunction: deleteForward,
                contentAfter: "<ul><li>abc</li><li>def[]</li></ul>",
            });
        });

        test("should remove the only character in a list", async () => {
            await testEditor({
                contentBefore: "<ul><li>[]a</li></ul>",
                stepFunction: deleteForward,
                contentAfter: "<ul><li>[]<br></li></ul>",
            });
            await testEditor({
                contentBefore: "<ul><li><p>[]a</p></li></ul>",
                stepFunction: deleteForward,
                contentAfter: "<ul><li><p>[]<br></p></li></ul>",
            });
        });

        test("should merge a list item with its next list item", async () => {
            await testEditor({
                contentBefore: "<ul><li>abc[]</li><li>def</li></ul>",
                stepFunction: deleteForward,
                contentAfter: "<ul><li>abc[]def</li></ul>",
            });
            // With another list item before.
            await testEditor({
                contentBefore: "<ul><li>abc</li><li>def[]</li><li>ghi</li></ul>",
                stepFunction: deleteForward,
                contentAfter: "<ul><li>abc</li><li>def[]ghi</li></ul>",
            });
            // Where the list item to merge into is empty, with an
            // empty list item before.
            await testEditor({
                contentBefore: "<ul><li><br></li><li>[]<br></li><li>abc</li></ul>",
                stepFunction: deleteForward,
                contentAfter: "<ul><li><br></li><li>[]abc</li></ul>",
            });
        });

        test("should rejoin sibling lists (ul)", async () => {
            await testEditor({
                contentBefore: "<ul><li>a[]</li></ul><p>b</p><ul><li>c</li></ul>",
                stepFunction: deleteForward,
                contentAfter: "<ul><li>a[]b</li><li>c</li></ul>",
            });
        });

        test("should rejoin multi-level sibling lists (1)", async () => {
            await testEditor({
                contentBefore: unformat(`
                            <ul>
                                <li><p>a</p>
                                    <ul>
                                        <li>b[]</li>
                                    </ul>
                                </li>
                            </ul>
                            <p>c</p>
                            <ul>
                                <li class="oe-nested">
                                    <ul>
                                        <li>d</li>
                                    </ul>
                                </li>
                                <li>e</li>
                            </ul>`),
                stepFunction: deleteForward,
                contentAfter: unformat(`
                            <ul>
                                <li><p>a</p>
                                    <ul>
                                        <li>b[]c</li>
                                        <li>d</li>
                                    </ul>
                                </li>
                                <li>e</li>
                            </ul>`),
            });
        });

        test("should only rejoin same-level lists (ol)", async () => {
            await testEditor({
                contentBefore: unformat(`
                            <ol>
                                <li><p>a</p>
                                    <ol>
                                        <li>b</li>
                                    </ol>
                                </li>
                                <li>c[]</li>
                            </ol>
                            <p>d</p>
                            <ol>
                                <li class="oe-nested">
                                    <ol>
                                        <li>e</li>
                                    </ol>
                                </li>
                                <li>f</li>
                            </ol>`),
                stepFunction: deleteForward,
                contentAfter: unformat(`
                            <ol>
                                <li><p>a</p>
                                    <ol>
                                        <li>b</li>
                                    </ol>
                                </li>
                                <li><p>c[]d</p>
                                    <ol>
                                        <li>e</li>
                                    </ol>
                                </li>
                                <li>f</li>
                            </ol>`),
            });
        });

        test("should not convert mixed lists on rejoin (ol)", async () => {
            await testEditor({
                contentBefore: "<ol><li>a[]</li></ol><p>b</p><ul><li>c</li></ul>",
                stepFunction: deleteForward,
                contentAfter: "<ol><li>a[]b</li></ol><ul><li>c</li></ul>",
            });
        });

        test("should not convert mixed multi-level lists on rejoin (ol)", async () => {
            await testEditor({
                contentBefore: unformat(`
                            <ol>
                                <li><p>a</p>
                                    <ul>
                                        <li>b[]</li>
                                    </ul>
                                </li>
                            </ol>
                            <p>c</p>
                            <ul>
                                <li class="oe-nested">
                                    <ul>
                                        <li>d</li>
                                    </ul>
                                </li>
                                <li>e</li>
                            </ul>`),
                stepFunction: deleteForward,
                contentAfter: unformat(`
                            <ol>
                                <li><p>a</p>
                                    <ul>
                                        <li>b[]c</li>
                                    </ul>
                                </li>
                            </ol>
                            <ul>
                                <li class="oe-nested">
                                    <ul>
                                        <li>d</li>
                                    </ul>
                                </li>
                                <li>e</li>
                            </ul>`),
            });
        });

        test("should delete the first character in a checklist item", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li class="o_checked">abc</li><li>[]defg</li></ul>',
                stepFunction: deleteForward,
                contentAfter:
                    '<ul class="o_checklist"><li class="o_checked">abc</li><li>[]efg</li></ul>',
            });
        });

        test("should delete a character within a checklist item", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li class="o_checked">abc</li><li>de[]fg</li></ul>',
                stepFunction: deleteForward,
                contentAfter:
                    '<ul class="o_checklist"><li class="o_checked">abc</li><li>de[]g</li></ul>',
            });
        });

        test("should delete the last character in a checklist item", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li class="o_checked">abc</li><li>def[]g</li></ul>',
                stepFunction: deleteForward,
                contentAfter:
                    '<ul class="o_checklist"><li class="o_checked">abc</li><li>def[]</li></ul>',
            });
        });

        test("should remove the only character in a checklist", async () => {
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li class="o_checked">[]a</li></ul>',
                stepFunction: deleteForward,
                contentAfter: '<ul class="o_checklist"><li class="o_checked">[]<br></li></ul>',
            });
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li class="o_checked"><p>[]a</p></li></ul>',
                stepFunction: deleteForward,
                contentAfter:
                    '<ul class="o_checklist"><li class="o_checked"><p>[]<br></p></li></ul>',
            });
        });

        test("should merge a checklist item with its next list item", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li class="o_checked">abc[]</li><li>def</li></ul>',
                stepFunction: deleteForward,
                contentAfter: '<ul class="o_checklist"><li class="o_checked">abc[]def</li></ul>',
            });
            // With another list item before.
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li class="o_checked">abc</li><li>def[]</li><li class="o_checked">ghi</li></ul>',
                stepFunction: deleteForward,
                contentAfter:
                    '<ul class="o_checklist"><li class="o_checked">abc</li><li>def[]ghi</li></ul>',
            });
            // Where the list item to merge into is empty, with an
            // empty list item before.
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li><br></li><li>[]<br></li><li>abc</li></ul>',
                stepFunction: deleteForward,
                contentAfter: '<ul class="o_checklist"><li><br></li><li>[]abc</li></ul>',
            });
        });

        test("should rejoin sibling lists (cl)", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li class="o_checked">a[]</li></ul><p>b</p><ul class="o_checklist"><li class="o_checked">c</li></ul>',
                stepFunction: deleteForward,
                contentAfter:
                    '<ul class="o_checklist"><li class="o_checked">a[]b</li><li class="o_checked">c</li></ul>',
            });
        });

        test("should rejoin multi-level sibling lists (2)", async () => {
            await testEditor({
                contentBefore: unformat(`
                            <ul class="o_checklist">
                                <li><p>a</p>
                                    <ul class="o_checklist">
                                        <li class="o_checked">b[]</li>
                                    </ul>
                                </li>
                            </ul>
                            <p>c</p>
                            <ul class="o_checklist">
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li>d</li>
                                    </ul>
                                </li>
                                <li>e</li>
                            </ul>`),
                stepFunction: deleteForward,
                contentAfter: unformat(`
                            <ul class="o_checklist">
                                <li><p>a</p>
                                    <ul class="o_checklist">
                                        <li class="o_checked">b[]c</li>
                                        <li>d</li>
                                    </ul>
                                </li>
                                <li>e</li>
                            </ul>`),
            });
        });

        test("should only rejoin same-level lists (ul)", async () => {
            await testEditor({
                contentBefore: unformat(`
                            <ul class="o_checklist">
                                <li><p>a</p>
                                    <ul class="o_checklist">
                                        <li class="o_checked">b</li>
                                    </ul>
                                </li>
                                <li class="o_checked">c[]</li>
                            </ul>
                            <p>d</p>
                            <ul class="o_checklist">
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li>e</li>
                                    </ul>
                                </li>
                                <li class="o_checked">f</li>
                            </ul>`),
                stepFunction: deleteForward,
                contentAfter: unformat(`
                            <ul class="o_checklist">
                                <li><p>a</p>
                                    <ul class="o_checklist">
                                        <li class="o_checked">b</li>
                                    </ul>
                                </li>
                                <li class="o_checked"><p>c[]d</p>
                                    <ul class="o_checklist">
                                        <li>e</li>
                                    </ul>
                                </li>
                                <li class="o_checked">f</li>
                            </ul>`),
            });
        });

        test("should not convert mixed lists on rejoin (ul)", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li class="o_checked">a[]</li></ul><p>b</p><ul><li>c</li></ul>',
                stepFunction: deleteForward,
                contentAfter:
                    '<ul class="o_checklist"><li class="o_checked">a[]b</li></ul><ul><li>c</li></ul>',
            });
        });

        test("should not convert mixed multi-level lists on rejoin (ul)", async () => {
            await testEditor({
                contentBefore: unformat(`
                            <ul class="o_checklist">
                                <li><p>a</p>
                                    <ul>
                                        <li class="o_checked">b[]</li>
                                    </ul>
                                </li>
                            </ul>
                            <p>c</p>
                            <ul>
                                <li class="oe-nested">
                                    <ul>
                                        <li>d</li>
                                    </ul>
                                </li>
                                <li>e</li>
                            </ul>`),
                stepFunction: deleteForward,
                contentAfter: unformat(`
                            <ul class="o_checklist">
                                <li><p>a</p>
                                    <ul>
                                        <li class="o_checked">b[]c</li>
                                    </ul>
                                </li>
                            </ul>
                            <ul>
                                <li class="oe-nested">
                                    <ul>
                                        <li>d</li>
                                    </ul>
                                </li>
                                <li>e</li>
                            </ul>`),
            });
        });
    });
    describe("Indented", () => {
        test("should merge an indented list item into a non-indented list item 1", async () => {
            await testEditor({
                contentBefore: "<ol><li><p>abc[]</p><ol><li>def</li><li>ghi</li></ol></li></ol>",
                stepFunction: async (editor) => {
                    deleteForward(editor);
                },
                contentAfter: "<ol><li><p>abc[]def</p><ol><li>ghi</li></ol></li></ol>",
            });
            await testEditor({
                contentBefore: "<ol><li><p>2bc[]</p><ol><li>def</li><li>ghi</li></ol></li></ol>",
                stepFunction: async (editor) => {
                    deleteForward(editor);
                    deleteForward(editor);
                },
                contentAfter: "<ol><li><p>2bc[]ef</p><ol><li>ghi</li></ol></li></ol>",
            });
        });

        test("should merge a non-indented list item into an indented list item", async () => {
            await testEditor({
                contentBefore:
                    '<ul><li class="oe-nested"><ul><li>abc[]</li></ul></li><li>def</li></ul>',
                stepFunction: deleteForward,
                contentAfter: '<ul><li class="oe-nested"><ul><li>abc[]def</li></ul></li></ul>',
            });
        });

        test("should merge the only item in an indented list into a non-indented list item and remove the now empty indented list", async () => {
            await testEditor({
                contentBefore: "<ul><li><p>abc[]</p><ul><li>def</li></ul></li></ul>",
                stepFunction: async (editor) => {
                    deleteForward(editor);
                    deleteForward(editor);
                },
                contentAfter: "<ul><li><p>abc[]ef</p></li></ul>",
            });
        });

        test("should merge an indented list item into a non-indented list item", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li><p>abc[]</p><ul class="o_checklist"><li>def</li><li class="o_checked">ghi</li></ul></li></ul>',
                stepFunction: async (editor) => {
                    deleteForward(editor);
                },
                contentAfter:
                    '<ul class="o_checklist"><li><p>abc[]def</p><ul class="o_checklist"><li class="o_checked">ghi</li></ul></li></ul>',
            });
        });

        test("should merge the only item in an indented list into a non-indented list item and remove the now empty indented list (2)", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li><p>abc[]</p><ul class="o_checklist"><li>def</li></ul></li></ul>',
                stepFunction: async (editor) => {
                    deleteForward(editor);
                },
                contentAfter: '<ul class="o_checklist"><li><p>abc[]def</p></li></ul>',
            });
        });
    });
    describe("Complex merges", () => {
        test("should merge a list item into a paragraph", async () => {
            await testEditor({
                contentBefore: "<p>ab[]cd</p><ul><li>ef</li><li>gh</li></ul>",
                stepFunction: async (editor) => {
                    deleteForward(editor);
                    deleteForward(editor);
                    deleteForward(editor);
                },
                contentAfter: "<p>ab[]ef</p><ul><li>gh</li></ul>",
            });
        });

        test("should merge a paragraph into a list item", async () => {
            await testEditor({
                contentBefore: "<ul><li>abc[]</li></ul><p>def</p>",
                stepFunction: deleteForward,
                contentAfter: "<ul><li>abc[]def</li></ul>",
            });
        });

        test("should merge a bold list item into a non-formatted list item", async () => {
            await testEditor({
                contentBefore:
                    "<ul><li>abc</li><li><b>de</b>fg[]</li><li><b>hij</b>klm</li><li>nop</li></ul>",
                stepFunction: deleteForward,
                contentAfter:
                    "<ul><li>abc</li><li><b>de</b>fg[]<b>hij</b>klm</li><li>nop</li></ul>",
            });
        });

        test("should merge a paragraph starting with bold text into a list item with ending without formatting", async () => {
            await testEditor({
                contentBefore: "<ul><li><i>abc</i>def[]</li></ul><p><b>ghi</b>jkl</p>",
                stepFunction: deleteForward,
                contentAfter: "<ul><li><i>abc</i>def[]<b>ghi</b>jkl</li></ul>",
            });
        });

        test("should merge a paragraph starting with bold text into a list item with ending with italic text", async () => {
            await testEditor({
                contentBefore: "<ul><li><b>abc</b><i>def[]</i></li></ul><p><b>ghi</b>jkl</p>",
                stepFunction: deleteForward,
                contentAfter: "<ul><li><b>abc</b><i>def[]</i><b>ghi</b>jkl</li></ul>",
            });
        });

        test("should merge a checklist item into a paragraph", async () => {
            await testEditor({
                contentBefore:
                    '<p>ab[]cd</p><ul class="o_checklist"><li class="o_checked">ef</li><li class="o_checked">gh</li></ul>',
                stepFunction: async (editor) => {
                    deleteForward(editor);
                    deleteForward(editor);
                    deleteForward(editor);
                    deleteForward(editor);
                },
                contentAfter:
                    '<p>ab[]f</p><ul class="o_checklist"><li class="o_checked">gh</li></ul>',
            });
        });

        test("should merge a paragraph into a checklist item", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li class="o_checked">abc[]</li></ul><p>def</p>',
                stepFunction: deleteForward,
                contentAfter: '<ul class="o_checklist"><li class="o_checked">abc[]def</li></ul>',
            });
        });

        test("should treat two blocks in a checklist item (checked/unchecked) as two list items and merge them", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li class="o_checked"><h1>abc</h1></li><li><h2>def[]</h2><h3>ghi</h3></li><li class="o_checked"><h4>klm</h4></li></ul>',
                stepFunction: deleteForward,
                // Paragraphs in list items are treated as nonsense.
                // unchecked folowed by checked
                contentAfter:
                    '<ul class="o_checklist"><li class="o_checked"><h1>abc</h1></li><li><h2>def[]ghi</h2></li><li class="o_checked"><h4>klm</h4></li></ul>',
            });
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li class="o_checked"><h1>abc</h1></li><li class="o_checked"><h2>def[]</h2><h3>ghi</h3></li><li><h4>klm</h4></li></ul>',
                stepFunction: deleteForward,
                // Paragraphs in list items are treated as nonsense.
                // checked folowed by unchecked
                contentAfter:
                    '<ul class="o_checklist"><li class="o_checked"><h1>abc</h1></li><li class="o_checked"><h2>def[]ghi</h2></li><li><h4>klm</h4></li></ul>',
            });
        });

        test("should merge a bold list item into a non-formatted list item (2)", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li>abc</li><li><b>de</b>fg[]</li><li><b>hij</b>klm</li><li>nop</li></ul>',
                stepFunction: deleteForward,
                // all checked
                contentAfter:
                    '<ul class="o_checklist"><li>abc</li><li><b>de</b>fg[]<b>hij</b>klm</li><li>nop</li></ul>',
            });
        });

        test("should merge a bold list item (checked/unchecked) into a non-formatted list item", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li class="o_checked">abc</li><li class="o_checked"><b>de</b>fg[]</li><li class="o_checked"><b>hij</b>klm</li><li class="o_checked">nop</li></ul>',
                stepFunction: deleteForward,
                // all checked
                contentAfter:
                    '<ul class="o_checklist"><li class="o_checked">abc</li><li class="o_checked"><b>de</b>fg[]<b>hij</b>klm</li><li class="o_checked">nop</li></ul>',
            });
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li class="o_checked">abc</li><li class="o_checked"><b>de</b>fg[]</li><li><b>hij</b>klm</li><li class="o_checked">nop</li></ul>',
                stepFunction: deleteForward,
                // only the removed li are unchecked
                contentAfter:
                    '<ul class="o_checklist"><li class="o_checked">abc</li><li class="o_checked"><b>de</b>fg[]<b>hij</b>klm</li><li class="o_checked">nop</li></ul>',
            });
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li>abc</li><li><b>de</b>fg[]</li><li class="o_checked"><b>hij</b>klm</li><li>nop</li></ul>',
                stepFunction: deleteForward,
                // only the removed li are checked
                contentAfter:
                    '<ul class="o_checklist"><li>abc</li><li><b>de</b>fg[]<b>hij</b>klm</li><li>nop</li></ul>',
            });
        });

        test("should merge a paragraph starting with bold text into a checklist item with ending without formatting", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li><i>abc</i>def[]</li></ul><p><b>ghi</b>jkl</p>',
                stepFunction: deleteForward,
                contentAfter: '<ul class="o_checklist"><li><i>abc</i>def[]<b>ghi</b>jkl</li></ul>',
            });
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li class="o_checked"><i>abc</i>def[]</li></ul><p><b>ghi</b>jkl</p>',
                stepFunction: deleteForward,
                // kepp checked
                contentAfter:
                    '<ul class="o_checklist"><li class="o_checked"><i>abc</i>def[]<b>ghi</b>jkl</li></ul>',
            });
        });

        test("should merge a paragraph starting with bold text into a checklist item with ending with italic text", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li><b>abc</b><i>def[]</i></li></ul><p><b>ghi</b>jkl</p>',
                stepFunction: deleteForward,
                contentAfter:
                    '<ul class="o_checklist"><li><b>abc</b><i>def[]</i><b>ghi</b>jkl</li></ul>',
            });
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li class="o_checked"><b>abc</b><i>def[]</i></li></ul><p><b>ghi</b>jkl</p>',
                stepFunction: deleteForward,
                // kepp checked
                contentAfter:
                    '<ul class="o_checklist"><li class="o_checked"><b>abc</b><i>def[]</i><b>ghi</b>jkl</li></ul>',
            });
        });
    });

    describe("Complex merges with some containers parsed in list item", () => {
        test("should treat two blocks in a list item and keep the blocks", async () => {
            await testEditor({
                contentBefore:
                    "<ul><li><h1>abc</h1></li><li><h2>def[]</h2><h3>ghi</h3></li><li><h4>klm</h4></li></ul>",
                stepFunction: deleteForward,
                // Paragraphs in list items are treated as nonsense.
                // Headings aren't, as they do provide extra information.
                contentAfter:
                    "<ul><li><h1>abc</h1></li><li><h2>def[]ghi</h2></li><li><h4>klm</h4></li></ul>",
            });
        });

        test("should treat two blocks in a checklist item and keep the blocks", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li class="o_checked"><h1>abc</h1></li><li class="o_checked"><h2>def[]</h2><h3>ghi</h3></li><li class="o_checked"><h4>klm</h4></li></ul>',
                stepFunction: deleteForward,
                contentAfter:
                    '<ul class="o_checklist"><li class="o_checked"><h1>abc</h1></li><li class="o_checked"><h2>def[]ghi</h2></li><li class="o_checked"><h4>klm</h4></li></ul>',
            });
        });
    });
});
describe("Selection not collapsed", () => {
    // Note: All tests on ordered lists should be duplicated
    // with unordered lists and checklists, and vice versae.
    describe("Ordered", () => {
        test("should delete text within a list item", async () => {
            // Forward selection
            await testEditor({
                contentBefore: "<ol><li>ab[cd]ef</li></ol>",
                stepFunction: deleteForward,
                contentAfter: "<ol><li>ab[]ef</li></ol>",
            });
            // Backward selection
            await testEditor({
                contentBefore: "<ol><li>ab]cd[ef</li></ol>",
                stepFunction: deleteForward,
                contentAfter: "<ol><li>ab[]ef</li></ol>",
            });
        });

        test("should delete all the text in a list item", async () => {
            // Forward selection
            await testEditor({
                contentBefore: "<ol><li>[abc]</li></ol>",
                stepFunction: deleteForward,
                contentAfter: "<ol><li>[]<br></li></ol>",
            });
            // Backward selection
            await testEditor({
                contentBefore: "<ol><li>]abc[</li></ol>",
                stepFunction: deleteForward,
                contentAfter: "<ol><li>[]<br></li></ol>",
            });
        });

        test("should delete across two list items", async () => {
            // Forward selection
            await testEditor({
                contentBefore: "<ol><li>ab[cd</li><li>ef]gh</li></ol>",
                stepFunction: deleteForward,
                contentAfter: "<ol><li>ab[]gh</li></ol>",
            });
            // Backward selection
            await testEditor({
                contentBefore: "<ol><li>ab]cd</li><li>ef[gh</li></ol>",
                stepFunction: deleteForward,
                contentAfter: "<ol><li>ab[]gh</li></ol>",
            });
        });

        test("should delete across an unindented list item and an indented list item", async () => {
            // Forward selection
            await testEditor({
                contentBefore: "<ol><li><p>ab[cd</p><ol><li>ef]gh</li></ol></li></ol>",
                stepFunction: deleteForward,
                contentAfter: "<ol><li><p>ab[]gh</p></li></ol>",
            });
            // Backward selection
            await testEditor({
                contentBefore: "<ol><li><p>ab]cd</p><ol><li>ef[gh</li></ol></li></ol>",
                stepFunction: deleteForward,
                contentAfter: "<ol><li><p>ab[]gh</p></li></ol>",
            });
        });

        test("should delete a list", async () => {
            // Forward selection
            await testEditor({
                contentBefore: "<p>abc[</p><ol><li><p>def]</p></li></ol>",
                stepFunction: deleteForward,
                contentAfter: "<p>abc[]</p>",
            });
            // Backward selection
            await testEditor({
                contentBefore: "<p>abc]</p><ol><li><p>def[</p></li></ol>",
                stepFunction: deleteForward,
                contentAfter: "<p>abc[]</p>",
            });
        });

        test("should merge the contents of a list item within a block into a heading, and leave the rest of its list as it is", async () => {
            // Forward selection
            await testEditor({
                contentBefore:
                    '<h1>a[b</h1><p>de</p><custom-block style="display:block;"><ol><li>fg</li><li>h]i</li><li>jk</li></ol></custom-block>',
                stepFunction: deleteForward,
                contentAfter:
                    '<h1>a[]i</h1><custom-block style="display:block;"><ol><li>jk</li></ol></custom-block>',
            });
            // Backward selection
            await testEditor({
                contentBefore:
                    '<h1>a]b</h1><p>de</p><custom-block style="display:block;"><ol><li>fg</li><li>h[i</li><li>jk</li></ol></custom-block>',
                stepFunction: deleteForward,
                contentAfter:
                    '<h1>a[]i</h1><custom-block style="display:block;"><ol><li>jk</li></ol></custom-block>',
            });
        });
    });

    describe("Unordered", () => {
        test("should delete text within a list item", async () => {
            // Forward selection
            await testEditor({
                contentBefore: "<ul><li>ab[cd]ef</li></ul>",
                stepFunction: deleteForward,
                contentAfter: "<ul><li>ab[]ef</li></ul>",
            });
            // Backward selection
            await testEditor({
                contentBefore: "<ul><li>ab]cd[ef</li></ul>",
                stepFunction: deleteForward,
                contentAfter: "<ul><li>ab[]ef</li></ul>",
            });
        });

        test("should delete all the text in a list item", async () => {
            // Forward selection
            await testEditor({
                contentBefore: "<ul><li>[abc]</li></ul>",
                stepFunction: deleteForward,
                contentAfter: "<ul><li>[]<br></li></ul>",
            });
            // Backward selection
            await testEditor({
                contentBefore: "<ul><li>]abc[</li></ul>",
                stepFunction: deleteForward,
                contentAfter: "<ul><li>[]<br></li></ul>",
            });
        });

        test("should delete across two list items", async () => {
            // Forward selection
            await testEditor({
                contentBefore: "<ul><li>ab[cd</li><li>ef]gh</li></ul>",
                stepFunction: deleteForward,
                contentAfter: "<ul><li>ab[]gh</li></ul>",
            });
            // Backward selection
            await testEditor({
                contentBefore: "<ul><li>ab]cd</li><li>ef[gh</li></ul>",
                stepFunction: deleteForward,
                contentAfter: "<ul><li>ab[]gh</li></ul>",
            });
        });

        test("should delete across an unindented list item and an indented list item", async () => {
            // Forward selection
            await testEditor({
                contentBefore: "<ul><li><p>ab[cd</p><ul><li>ef]gh</li></ul></li></ul>",
                stepFunction: deleteForward,
                contentAfter: "<ul><li><p>ab[]gh</p></li></ul>",
            });
            // Backward selection
            await testEditor({
                contentBefore: "<ul><li><p>ab]cd</p><ul><li>ef[gh</li></ul></li></ul>",
                stepFunction: deleteForward,
                contentAfter: "<ul><li><p>ab[]gh</p></li></ul>",
            });
        });

        test("should delete a list", async () => {
            // Forward selection
            await testEditor({
                contentBefore: "<p>abc[</p><ul><li><p>def]</p></li></ul>",
                stepFunction: deleteForward,
                contentAfter: "<p>abc[]</p>",
            });
            // Backward selection
            await testEditor({
                contentBefore: "<p>abc]</p><ul><li><p>def[</p></li></ul>",
                stepFunction: deleteForward,
                contentAfter: "<p>abc[]</p>",
            });
        });

        test("should merge the contents of a list item within a block into a heading, and leave the rest of its list as it is", async () => {
            // Forward selection
            await testEditor({
                contentBefore:
                    '<h1>a[b</h1><p>de</p><custom-block style="display: block;"><ul><li>fg</li><li>h]i</li><li>jk</li></ul></custom-block>',
                stepFunction: deleteForward,
                contentAfter:
                    '<h1>a[]i</h1><custom-block style="display: block;"><ul><li>jk</li></ul></custom-block>',
            });
            // Backward selection
            await testEditor({
                contentBefore:
                    '<h1>a]b</h1><p>de</p><custom-block style="display: block;"><ul><li>fg</li><li>h[i</li><li>jk</li></ul></custom-block>',
                stepFunction: deleteForward,
                contentAfter:
                    '<h1>a[]i</h1><custom-block style="display: block;"><ul><li>jk</li></ul></custom-block>',
            });
        });
    });
    describe("Checklist", () => {
        test("should delete text within a checklist item", async () => {
            // Forward selection
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li class="o_checked">ab[cd]ef</li></ul>',
                stepFunction: deleteForward,
                contentAfter: '<ul class="o_checklist"><li class="o_checked">ab[]ef</li></ul>',
            });
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li>ab[cd]ef</li></ul>',
                stepFunction: deleteForward,
                contentAfter: '<ul class="o_checklist"><li>ab[]ef</li></ul>',
            });
            // Backward selection
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li class="o_checked">ab]cd[ef</li></ul>',
                stepFunction: deleteForward,
                contentAfter: '<ul class="o_checklist"><li class="o_checked">ab[]ef</li></ul>',
            });
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li>ab]cd[ef</li></ul>',
                stepFunction: deleteForward,
                contentAfter: '<ul class="o_checklist"><li>ab[]ef</li></ul>',
            });
        });

        test("should delete all the text in a checklist item", async () => {
            // Forward selection
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li class="o_checked">[abc]</li></ul>',
                stepFunction: deleteForward,
                contentAfter: '<ul class="o_checklist"><li class="o_checked">[]<br></li></ul>',
            });
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li>[abc]</li></ul>',
                stepFunction: deleteForward,
                contentAfter: '<ul class="o_checklist"><li>[]<br></li></ul>',
            });
            // Backward selection
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li class="o_checked">]abc[</li></ul>',
                stepFunction: deleteForward,
                contentAfter: '<ul class="o_checklist"><li class="o_checked">[]<br></li></ul>',
            });
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li>]abc[</li></ul>',
                stepFunction: deleteForward,
                contentAfter: '<ul class="o_checklist"><li>[]<br></li></ul>',
            });
        });

        describe("should delete across two list items", () => {});
        // Forward selection
        test("should delete across two list items (1)", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li class="o_checked">ab[cd</li><li class="o_checked">ef]gh</li></ul>',
                stepFunction: deleteForward,
                contentAfter: '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
            });
        });
        test("should delete across two list items (2)", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li class="o_checked">ab[cd</li><li>ef]gh</li></ul>',
                stepFunction: deleteForward,
                contentAfter: '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
            });
        });
        test("should delete across two list items (3)", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li>ab[cd</li><li class="o_checked">ef]gh</li></ul>',
                stepFunction: deleteForward,
                contentAfter: '<ul class="o_checklist"><li>ab[]gh</li></ul>',
            });
        });
        test("should delete across two list items (4)", async () => {
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li>ab[cd</li><li>ef]gh</li></ul>',
                stepFunction: deleteForward,
                contentAfter: '<ul class="o_checklist"><li>ab[]gh</li></ul>',
            });
        });
        // Backward selection
        test("should delete across two list items (5)", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li class="o_checked">ab]cd</li><li class="o_checked">ef[gh</li></ul>',
                stepFunction: deleteForward,
                contentAfter: '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
            });
        });
        test("should delete across two list items (6)", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li>ab]cd</li><li class="o_checked">ef[gh</li></ul>',
                stepFunction: deleteForward,
                contentAfter: '<ul class="o_checklist"><li>ab[]gh</li></ul>',
            });
        });
        test("should delete across two list items (7)", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li class="o_checked">ab]cd</li><li>ef[gh</li></ul>',
                stepFunction: deleteForward,
                contentAfter: '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
            });
        });
        test("should delete across two list items (8)", async () => {
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li>ab]cd</li><li>ef[gh</li></ul>',
                stepFunction: deleteForward,
                contentAfter: '<ul class="o_checklist"><li>ab[]gh</li></ul>',
            });
        });
    });

    describe("should delete across an unindented list item and an indented list item", () => {
        // Forward selection
        test("should delete across an unindented list item and an indented list item (1)", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li><p>ab[cd</p><ul class="o_checklist"><li class="o_checked">ef]gh</li></ul></li></ul>',
                stepFunction: deleteForward,
                contentAfter: '<ul class="o_checklist"><li><p>ab[]gh</p></li></ul>',
            });
        });
        test("should delete across an unindented list item and an indented list item (2)", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li><p>ab[cd</p><ul class="o_checklist"><li>ef]gh</li></ul></li></ul>',
                stepFunction: deleteForward,
                // The indented list's parent gets rendered as
                // checked because its only child is checked.
                contentAfter: '<ul class="o_checklist"><li><p>ab[]gh</p></li></ul>',
            });
        });
        test("should delete across an unindented list item and an indented list item (3)", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li><p>ab[cd</p><ul class="o_checklist"><li class="o_checked">ef]gh</li></ul></li></ul>',
                stepFunction: deleteForward,
                // The indented list's parent gets rendered as
                // checked because its only child is checked. When
                // we remove that child, the checklist gets
                // unchecked because it becomes independant again.
                contentAfter: '<ul class="o_checklist"><li><p>ab[]gh</p></li></ul>',
            });
        });
        // Backward selection
        test("should delete across an unindented list item and an indented list item (4)", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li><p>ab]cd</p><ul class="o_checklist"><li class="o_checked">ef[gh</li></ul></li></ul>',
                stepFunction: deleteForward,
                contentAfter: '<ul class="o_checklist"><li><p>ab[]gh</p></li></ul>',
            });
        });
        test("should delete across an unindented list item and an indented list item (5)", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li><p>ab]cd</p><ul class="o_checklist"><li>ef[gh</li></ul></li></ul>',
                stepFunction: deleteForward,
                // The indented list's parent gets rendered as
                // checked because its only child is checked.
                contentAfter: '<ul class="o_checklist"><li><p>ab[]gh</p></li></ul>',
            });
        });
        test("should delete across an unindented list item and an indented list item (6)", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li><p>ab]cd</p><ul class="o_checklist"><li class="o_checked">ef[gh</li></ul></li></ul>',
                stepFunction: deleteForward,
                // The indented list's parent gets rendered as
                // checked because its only child is checked. When
                // we remove that child, the checklist gets
                // unchecked because it becomes independant again.
                contentAfter: '<ul class="o_checklist"><li><p>ab[]gh</p></li></ul>',
            });
        });
    });

    test("should delete a checklist", async () => {
        // Forward selection
        await testEditor({
            contentBefore: '<p>abc[</p><ul class="o_checklist"><li><p>def]</p></li></ul>',
            stepFunction: deleteForward,
            contentAfter: "<p>abc[]</p>",
        });
        // Backward selection
        await testEditor({
            contentBefore: '<p>abc]</p><ul class="o_checklist"><li><p>def[</p></li></ul>',
            stepFunction: deleteForward,
            contentAfter: "<p>abc[]</p>",
        });
    });

    describe("should merge the contents of a checklist item within a block into a heading, and leave the rest of its list as it is", () => {
        // Forward selection
        test("should merge the contents of a checklist item within a block into a heading, and leave the rest of its list as it is (1)", async () => {
            await testEditor({
                contentBefore:
                    '<h1>a[b</h1><p>de</p><custom-block style="display: block;"><ul class="o_checklist"><li class="o_checked">fg</li><li>h]i</li><li class="o_checked">jk</li></ul></custom-block>',
                stepFunction: deleteForward,
                contentAfter:
                    '<h1>a[]i</h1><custom-block style="display: block;"><ul class="o_checklist"><li class="o_checked">jk</li></ul></custom-block>',
            });
        });
        test("should merge the contents of a checklist item within a block into a heading, and leave the rest of its list as it is (2)", async () => {
            await testEditor({
                contentBefore:
                    '<h1>a[b</h1><p>de</p><custom-block style="display: block;"><ul class="o_checklist"><li>fg</li><li>h]i</li><li class="o_checked">jk</li></ul></custom-block>',
                stepFunction: deleteForward,
                contentAfter:
                    '<h1>a[]i</h1><custom-block style="display: block;"><ul class="o_checklist"><li class="o_checked">jk</li></ul></custom-block>',
            });
        });
        test("should merge the contents of a checklist item within a block into a heading, and leave the rest of its list as it is (3)", async () => {
            await testEditor({
                contentBefore:
                    '<h1>a[b</h1><p>de</p><custom-block style="display: block;"><ul class="o_checklist"><li class="o_checked">fg</li><li>h]i</li><li>jk</li></ul></custom-block>',
                stepFunction: deleteForward,
                contentAfter:
                    '<h1>a[]i</h1><custom-block style="display: block;"><ul class="o_checklist"><li>jk</li></ul></custom-block>',
            });
        });
        test("should merge the contents of a checklist item within a block into a heading, and leave the rest of its list as it is (4)", async () => {
            await testEditor({
                contentBefore:
                    '<h1>a[b</h1><p>de</p><custom-block style="display: block;"><ul class="o_checklist"><li>fg</li><li>h]i</li><li>jk</li></ul></custom-block>',
                stepFunction: deleteForward,
                contentAfter:
                    '<h1>a[]i</h1><custom-block style="display: block;"><ul class="o_checklist"><li>jk</li></ul></custom-block>',
            });
        });
        // Backward selection
        test("should merge the contents of a checklist item within a block into a heading, and leave the rest of its list as it is (5)", async () => {
            await testEditor({
                contentBefore:
                    '<h1>a]b</h1><p>de</p><custom-block style="display: block;"><ul class="o_checklist"><li>fg</li><li class="o_checked">h[i</li><li class="o_checked">jk</li></ul></custom-block>',
                stepFunction: deleteForward,
                contentAfter:
                    '<h1>a[]i</h1><custom-block style="display: block;"><ul class="o_checklist"><li class="o_checked">jk</li></ul></custom-block>',
            });
        });
        test("should merge the contents of a checklist item within a block into a heading, and leave the rest of its list as it is (6)", async () => {
            await testEditor({
                contentBefore:
                    '<h1>a]b</h1><p>de</p><custom-block style="display: block;"><ul class="o_checklist"><li>fg</li><li>h[i</li><li class="o_checked">jk</li></ul></custom-block>',
                stepFunction: deleteForward,
                contentAfter:
                    '<h1>a[]i</h1><custom-block style="display: block;"><ul class="o_checklist"><li class="o_checked">jk</li></ul></custom-block>',
            });
        });
        test("should merge the contents of a checklist item within a block into a heading, and leave the rest of its list as it is (7)", async () => {
            await testEditor({
                contentBefore:
                    '<h1>a]b</h1><p>de</p><custom-block style="display: block;"><ul class="o_checklist"><li>fg</li><li class="o_checked">h[i</li><li>jk</li></ul></custom-block>',
                stepFunction: deleteForward,
                contentAfter:
                    '<h1>a[]i</h1><custom-block style="display: block;"><ul class="o_checklist"><li>jk</li></ul></custom-block>',
            });
        });
        test("should merge the contents of a checklist item within a block into a heading, and leave the rest of its list as it is (8)", async () => {
            await testEditor({
                contentBefore:
                    '<h1>a]b</h1><p>de</p><custom-block style="display: block;"><ul class="o_checklist"><li>fg</li><li>h[i</li><li>jk</li></ul></custom-block>',
                stepFunction: deleteForward,
                contentAfter:
                    '<h1>a[]i</h1><custom-block style="display: block;"><ul class="o_checklist"><li>jk</li></ul></custom-block>',
            });
        });
    });
    describe("Mixed", () => {
        describe("Ordered to unordered", () => {
            test("should delete across an ordered list and an unordered list", async () => {
                // Forward selection
                await testEditor({
                    contentBefore: "<ol><li>ab[cd</li></ol><ul><li>ef]gh</li></ul>",
                    stepFunction: deleteForward,
                    contentAfter: "<ol><li>ab[]gh</li></ol>",
                });
                // Backward selection
                await testEditor({
                    contentBefore: "<ol><li>ab]cd</li></ol><ul><li>ef[gh</li></ul>",
                    stepFunction: deleteForward,
                    contentAfter: "<ol><li>ab[]gh</li></ol>",
                });
            });

            test("should delete across an ordered list item and an unordered list item within an ordered list", async () => {
                // Forward selection
                await testEditor({
                    contentBefore: "<ol><li><p>ab[cd</p><ul><li>ef]gh</li></ul></li></ol>",
                    stepFunction: deleteForward,
                    contentAfter: "<ol><li><p>ab[]gh</p></li></ol>",
                });
                // Backward selection
                await testEditor({
                    contentBefore: "<ol><li><p>ab]cd</p><ul><li>ef[gh</li></ul></li></ol>",
                    stepFunction: deleteForward,
                    contentAfter: "<ol><li><p>ab[]gh</p></li></ol>",
                });
            });

            test("should delete an ordered list and an unordered list", async () => {
                // Forward selection
                await testEditor({
                    contentBefore: "<p>ab[</p><ul><li>cd</li></ul><ol><li>ef]</li></ol>",
                    stepFunction: deleteForward,
                    contentAfter: "<p>ab[]</p>",
                });
                // Backward selection
                await testEditor({
                    contentBefore: "<p>ab]</p><ul><li>cd</li></ul><ol><li>ef[</li></ol>",
                    stepFunction: deleteForward,
                    contentAfter: "<p>ab[]</p>",
                });
            });
        });
        describe("Unordered to ordered", () => {
            test("should delete across an unordered list and an ordered list", async () => {
                // Forward selection
                await testEditor({
                    contentBefore: "<ul><li>ab[cd</li></ul><ol><li>ef]gh</li></ol>",
                    stepFunction: deleteForward,
                    contentAfter: "<ul><li>ab[]gh</li></ul>",
                });
                // Backward selection
                await testEditor({
                    contentBefore: "<ul><li>ab]cd</li></ul><ol><li>ef[gh</li></ol>",
                    stepFunction: deleteForward,
                    contentAfter: "<ul><li>ab[]gh</li></ul>",
                });
            });

            test("should delete across an unordered list item and an ordered list item within an unordered list", async () => {
                // Forward selection
                await testEditor({
                    contentBefore: "<ul><li><p>ab[cd</p><ol><li>ef]gh</li></ol></li></ul>",
                    stepFunction: deleteForward,
                    contentAfter: "<ul><li><p>ab[]gh</p></li></ul>",
                });
                // Backward selection
                await testEditor({
                    contentBefore: "<ul><li><p>ab]cd</p><ol><li>ef[gh</li></ol></li></ul>",
                    stepFunction: deleteForward,
                    contentAfter: "<ul><li><p>ab[]gh</p></li></ul>",
                });
            });

            test("should delete an ordered list and an unordered list", async () => {
                // Forward selection
                await testEditor({
                    contentBefore: "<p>ab[</p><ol><li>cd</li></ol><ul><li>ef]</li></ul>",
                    stepFunction: deleteForward,
                    contentAfter: "<p>ab[]</p>",
                });
                // Backward selection
                await testEditor({
                    contentBefore: "<p>ab]</p><ol><li>cd</li></ol><ul><li>ef[</li></ul>",
                    stepFunction: deleteForward,
                    contentAfter: "<p>ab[]</p>",
                });
            });
        });
        describe("Checklist to unordered", () => {
            describe("should delete across an checklist list and an unordered list", () => {
                test("should delete across an checklist list and an unordered list (1)", async () => {
                    // Forward selection
                    await testEditor({
                        contentBefore:
                            '<ul class="o_checklist"><li class="o_checked">ab[cd</li></ul><ul><li class="o_checked">ef]gh</li></ul>',
                        stepFunction: deleteForward,
                        contentAfter:
                            '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                    });
                });
                test("should delete across an checklist list and an unordered list (2)", async () => {
                    await testEditor({
                        contentBefore:
                            '<ul class="o_checklist"><li>ab[cd</li></ul><ul><li class="o_checked">ef]gh</li></ul>',
                        stepFunction: deleteForward,
                        contentAfter: '<ul class="o_checklist"><li>ab[]gh</li></ul>',
                    });
                });
                test("should delete across an checklist list and an unordered list (3)", async () => {
                    await testEditor({
                        contentBefore:
                            '<ul class="o_checklist"><li class="o_checked">ab[cd</li></ul><ul><li>ef]gh</li></ul>',
                        stepFunction: deleteForward,
                        contentAfter:
                            '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                    });
                });
                test("should delete across an checklist list and an unordered list (4)", async () => {
                    await testEditor({
                        contentBefore:
                            '<ul class="o_checklist"><li>ab[cd</li></ul><ul><li>ef]gh</li></ul>',
                        stepFunction: deleteForward,
                        contentAfter: '<ul class="o_checklist"><li>ab[]gh</li></ul>',
                    });
                });
                test("should delete across an checklist list and an unordered list (5)", async () => {
                    // Backward selection
                    await testEditor({
                        contentBefore:
                            '<ul class="o_checklist"><li class="o_checked">ab]cd</li></ul><ul><li class="o_checked">ef[gh</li></ul>',
                        stepFunction: deleteForward,
                        contentAfter:
                            '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                    });
                });
                test("should delete across an checklist list and an unordered list (6)", async () => {
                    await testEditor({
                        contentBefore:
                            '<ul class="o_checklist"><li>ab]cd</li></ul><ul><li class="o_checked">ef[gh</li></ul>',
                        stepFunction: deleteForward,
                        contentAfter: '<ul class="o_checklist"><li>ab[]gh</li></ul>',
                    });
                });
                test("should delete across an checklist list and an unordered list (7)", async () => {
                    await testEditor({
                        contentBefore:
                            '<ul class="o_checklist"><li class="o_checked">ab]cd</li></ul><ul><li>ef[gh</li></ul>',
                        stepFunction: deleteForward,
                        contentAfter:
                            '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                    });
                });
                test("should delete across an checklist list and an unordered list (8)", async () => {
                    await testEditor({
                        contentBefore:
                            '<ul class="o_checklist"><li>ab]cd</li></ul><ul><li>ef[gh</li></ul>',
                        stepFunction: deleteForward,
                        contentAfter: '<ul class="o_checklist"><li>ab[]gh</li></ul>',
                    });
                });
            });

            describe("should delete across an checklist list item and an unordered list item within an checklist list", () => {
                // Forward selection
                test("should delete across an checklist list item and an unordered list item within an checklist list (1)", async () => {
                    await testEditor({
                        contentBefore:
                            '<ul class="o_checklist"><li><p>ab[cd</p><ul><li class="o_checked">ef]gh</li></ul></li></ul>',
                        stepFunction: deleteForward,
                        contentAfter: '<ul class="o_checklist"><li><p>ab[]gh</p></li></ul>',
                    });
                });
                test("should delete across an checklist list item and an unordered list item within an checklist list (2)", async () => {
                    await testEditor({
                        contentBefore:
                            '<ul class="o_checklist"><li><p>ab[cd</p><ul><li>ef]gh</li></ul></li></ul>',
                        stepFunction: deleteForward,
                        contentAfter: '<ul class="o_checklist"><li><p>ab[]gh</p></li></ul>',
                    });
                });
                // Backward selection
                test("should delete across an checklist list item and an unordered list item within an checklist list (3)", async () => {
                    await testEditor({
                        contentBefore:
                            '<ul class="o_checklist"><li><p>ab]cd</p><ul><li class="o_checked">ef[gh</li></ul></li></ul>',
                        stepFunction: deleteForward,
                        contentAfter: '<ul class="o_checklist"><li><p>ab[]gh</p></li></ul>',
                    });
                });
                test("should delete across an checklist list item and an unordered list item within an checklist list (4)", async () => {
                    await testEditor({
                        contentBefore:
                            '<ul class="o_checklist"><li><p>ab]cd</p><ul><li>ef[gh</li></ul></li></ul>',
                        stepFunction: deleteForward,
                        contentAfter: '<ul class="o_checklist"><li><p>ab[]gh</p></li></ul>',
                    });
                });
            });

            test("should delete an checklist list and an unordered list", async () => {
                // Forward selection
                await testEditor({
                    contentBefore:
                        '<p>ab[</p><ul><li>cd</li></ul><ul class="o_checklist"><li class="o_checked">ef]</li></ul>',
                    stepFunction: deleteForward,
                    contentAfter: "<p>ab[]</p>",
                });
                // Backward selection
                await testEditor({
                    contentBefore:
                        '<p>ab]</p><ul><li>cd</li></ul><ul class="o_checklist"><li class="o_checked">ef[</li></ul>',
                    stepFunction: deleteForward,
                    contentAfter: "<p>ab[]</p>",
                });
            });
        });
        describe("Unordered to checklist", () => {
            test("should delete across an unordered list and an checklist list", async () => {
                // Forward selection
                await testEditor({
                    contentBefore:
                        '<ul><li>ab[cd</li></ul><ul class="o_checklist"><li class="o_checked">ef]gh</li></ul>',
                    stepFunction: deleteForward,
                    contentAfter: "<ul><li>ab[]gh</li></ul>",
                });
                // Backward selection
                await testEditor({
                    contentBefore:
                        '<ul><li>ab]cd</li></ul><ul class="o_checklist"><li>ef[gh</li></ul>',
                    stepFunction: deleteForward,
                    contentAfter: "<ul><li>ab[]gh</li></ul>",
                });
            });

            test("should delete across an unordered list item and an checklist list item within an unordered list", async () => {
                // Forward selection
                await testEditor({
                    contentBefore:
                        '<ul><li><p>ab[cd</p><ul class="o_checklist"><li class="o_checked">ef]gh</li></ul></li></ul>',
                    stepFunction: deleteForward,
                    contentAfter: "<ul><li><p>ab[]gh</p></li></ul>",
                });
                // Backward selection
                await testEditor({
                    contentBefore:
                        '<ul><li><p>ab]cd</p><ul class="o_checklist"><li class="o_checked">ef[gh</li></ul></li></ul>',
                    stepFunction: deleteForward,
                    contentAfter: "<ul><li><p>ab[]gh</p></li></ul>",
                });
            });

            test("should delete an checklist list and an unordered list", async () => {
                // Forward selection
                await testEditor({
                    contentBefore:
                        '<p>ab[</p><ul class="o_checklist"><li class="o_checked">cd</li></ul><ul><li>ef]</li></ul>',
                    stepFunction: deleteForward,
                    contentAfter: "<p>ab[]</p>",
                });
                // Backward selection
                await testEditor({
                    contentBefore:
                        '<p>ab]</p><ul class="o_checklist"><li class="o_checked">cd</li></ul><ul><li>ef[</li></ul>',
                    stepFunction: deleteForward,
                    contentAfter: "<p>ab[]</p>",
                });
            });
        });
    });
});
