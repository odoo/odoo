import { test, describe } from "@odoo/hoot";
import { testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { deleteBackward } from "../_helpers/user_actions";

describe("Selection collapsed", () => {
    // Note: All tests on ordered lists should be duplicated
    // with unordered lists and checklists, and vice versae.
    describe("Ordered", () => {
        describe("Basic", () => {
            test("should convert to paragraph", async () => {
                await testEditor({
                    contentBefore: "<ol><li><br>[]</li></ol>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>[]<br></p>",
                });
                await testEditor({
                    contentBefore: '<ol><li class="oe-nested"><ol><li>[]abc</li></ol></li></ol>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>[]abc</p>",
                });
            });

            test("should delete the first character in a list item", async () => {
                await testEditor({
                    contentBefore: "<ol><li>abc</li><li>d[]efg</li></ol>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ol><li>abc</li><li>[]efg</li></ol>",
                });
            });

            test("should delete a character within a list item", async () => {
                await testEditor({
                    contentBefore: "<ol><li>abc</li><li>de[]fg</li></ol>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ol><li>abc</li><li>d[]fg</li></ol>",
                });
            });

            test("should delete the last character in a list item", async () => {
                await testEditor({
                    contentBefore: "<ol><li>abc</li><li>defg[]</li></ol>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ol><li>abc</li><li>def[]</li></ol>",
                });
            });

            test("should remove the only character in a list", async () => {
                await testEditor({
                    contentBefore: "<ol><li>a[]</li></ol>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ol><li>[]<br></li></ol>",
                });
                await testEditor({
                    contentBefore: "<ol><li><p>a[]</p></li></ol>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ol><li><p>[]<br></p></li></ol>",
                });
            });

            test("should merge a list item with its previous list item", async () => {
                await testEditor({
                    contentBefore: "<ol><li>abc</li><li>[]def</li></ol>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ol><li>abc</li></ol><p>[]def</p>",
                });
                // With another list item after.
                await testEditor({
                    contentBefore: "<ol><li>abc</li><li>[]def</li><li>ghi</li></ol>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ol><li>abc</li></ol><p>[]def</p><ol><li>ghi</li></ol>",
                });
                // Where the list item to merge into is empty, with an
                // empty list item before.
                await testEditor({
                    contentBefore: "<ol><li><br></li><li><br></li><li>[]abc</li></ol>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ol><li><br></li><li><br></li></ol><p>[]abc</p>",
                });
            });

            test("should rejoin sibling lists (ol)", async () => {
                await testEditor({
                    contentBefore: "<ol><li>a</li></ol><p>[]b</p><ol><li>c</li></ol>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ol><li>a[]b</li><li>c</li></ol>",
                });
            });

            test("should rejoin multi-level sibling lists", async () => {
                await testEditor({
                    contentBefore: unformat(`
                            <ul>
                                <li><p>a</p>
                                    <ul>
                                        <li>b</li>
                                    </ul>
                                </li>
                            </ul>
                            <p>[]c</p>
                            <ul>
                                <li class="oe-nested">
                                    <ul>
                                        <li>d</li>
                                    </ul>
                                </li>
                                <li>e</li>
                            </ul>`),
                    stepFunction: deleteBackward,
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

            test("should only rejoin same-level lists", async () => {
                await testEditor({
                    contentBefore: unformat(`
                            <ol>
                                <li><p>a</p>
                                    <ol>
                                        <li>b</li>
                                    </ol>
                                </li>
                                <li>c</li>
                            </ol>
                            <p>[]d</p>
                            <ol>
                                <li class="oe-nested">
                                    <ol>
                                        <li>e</li>
                                    </ol>
                                </li>
                                <li>f</li>
                            </ol>`),
                    stepFunction: deleteBackward,
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

            test("should not convert mixed lists on rejoin", async () => {
                await testEditor({
                    contentBefore: "<ol><li>a</li></ol><p>[]b</p><ul><li>c</li></ul>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ol><li>a[]b</li></ol><ul><li>c</li></ul>",
                });
            });

            test("should not convert mixed multi-level lists on rejoin", async () => {
                await testEditor({
                    contentBefore: unformat(`
                            <ol>
                                <li><p>a</p>
                                    <ul>
                                        <li>b</li>
                                    </ul>
                                </li>
                            </ol>
                            <p>[]c</p>
                            <ul>
                                <li class="oe-nested">
                                    <ul>
                                        <li>d</li>
                                    </ul>
                                </li>
                                <li>e</li>
                            </ul>`),
                    stepFunction: deleteBackward,
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
        });
        describe("Indented", () => {
            test("should merge an indented list item into a non-indented list item", async () => {
                await testEditor({
                    contentBefore:
                        "<ol><li><p>abc</p><ol><li>[]def</li><li>ghi</li></ol></li></ol>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ol><li><p>abc[]def</p><ol><li>ghi</li></ol></li></ol>",
                });
            });

            test("should merge a non-indented list item into an indented list item", async () => {
                await testEditor({
                    contentBefore:
                        '<ol><li class="oe-nested"><ol><li>abc</li></ol></li><li>[]def</li></ol>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter:
                        '<ol><li class="oe-nested"><ol><li>abc</li></ol></li></ol><p>[]def</p>',
                });
            });

            test("should merge the only item in an indented list into a non-indented list item and remove the now empty indented list", async () => {
                await testEditor({
                    contentBefore: "<ol><li><p>abc</p><ol><li>[]def</li></ol></li></ol>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ol><li><p>abc[]def</p></li></ol>",
                });
            });

            test("should outdent a list item", async () => {
                await testEditor({
                    contentBefore: '<ol><li class="oe-nested"><ol><li>[]abc</li></ol></li></ol>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>[]abc</p>",
                });
                // With a paragraph before the list:
                await testEditor({
                    contentBefore:
                        '<p>abc</p><ol><li class="oe-nested"><ol><li>[]def</li></ol></li></ol>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>abc</p><p>[]def</p>",
                });
            });

            test.skip("should outdent while nested within a list item", async () => {
                await testEditor({
                    contentBefore:
                        "<ol><li><div>abc</div></li><li><div><div>[]def</div></div></li></ol>",
                    stepFunction: deleteBackward,
                    // TODO: the additional DIV used to represent
                    // the LI. The ideal result would be:
                    //contentAfter: '<ol><li><div>abc</div></li></ol><div><div>[]def</div></div>',
                    contentAfter:
                        "<ol><li><div>abc</div></li></ol><div><div><div>[]def</div></div></div>",
                });
                // With a div before the list:
                await testEditor({
                    contentBefore: "<div>abc</div><ol><li><div><div>[]def</div></div></li></ol>",
                    stepFunction: deleteBackward,
                    // TODO: the additional DIV used to represent
                    // the LI. The ideal result would be:
                    // contentAfter: '<div>abc</div><div><div>[]def</div></div>',
                    contentAfter: "<div>abc</div><div><div><div>[]def</div></div></div>",
                });
            });

            test("should outdent an empty list item within a list", async () => {
                await testEditor({
                    contentBefore:
                        "<ol><li><p>abc</p><ol><li>[]<br></li><li><br></li></ol></li><li>def</li></ol>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter:
                        '<ol><li><p>abc</p></li></ol><p>[]<br></p><ol><li class="oe-nested"><ol><li><br></li></ol></li><li>def</li></ol>',
                });
            });

            test("should outdent an empty list within a list", async () => {
                await testEditor({
                    contentBefore:
                        "<ol><li><p>abc</p><ol><li>[]<br></li></ol></li><li>def</li></ol>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ol><li><p>abc</p></li></ol><p>[]<br></p><ol><li>def</li></ol>",
                });
            });

            test("should outdent an empty list", async () => {
                await testEditor({
                    contentBefore: '<ol><li class="oe-nested"><ol><li><br>[]</li></ol></li></ol>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>[]<br></p>",
                });
            });

            test("should outdent a list to the point that it's a paragraph", async () => {
                await testEditor({
                    contentBefore: "<ol><li>[]<br></li></ol>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>[]<br></p>",
                });
                // With a paragraph before the list:
                await testEditor({
                    contentBefore: "<p><br></p><ol><li>[]<br></li></ol>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p><br></p><p>[]<br></p>",
                });
            });

            test("should outdent an empty list to a paragraph in the list's direction", async () => {
                await testEditor({
                    contentBefore: unformat(`
                        <ul>
                            <li><p>abc</p>
                                <ul dir="rtl" style="text-align: right;">
                                    <li>abc</li>
                                    <li>[]<br></li>
                                </ul>
                            </li>
                        </ul>`),
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: unformat(`
                        <ul>
                            <li><p>abc</p>
                                <ul dir="rtl" style="text-align: right;">
                                    <li>abc</li>
                                </ul>
                            </li>
                        </ul>
                        <p dir="rtl">[]<br></p>`),
                });
            });
        });
        describe("Complex merges", () => {
            test("should merge a list item into a paragraph", async () => {
                await testEditor({
                    contentBefore: "<p>abcd</p><ol><li>ef[]gh</li><li>ij</li></ol>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>abcd[]gh</p><ol><li>ij</li></ol>",
                });
            });

            test("should merge a paragraph into a list item", async () => {
                await testEditor({
                    contentBefore: "<ol><li>abc</li></ol><p>[]def</p>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ol><li>abc[]def</li></ol>",
                });
            });

            test("should merge a paragraph starting with bold text into a list item with ending without formatting", async () => {
                await testEditor({
                    contentBefore: "<ol><li><i>abc</i>def</li></ol><p><b>[]ghi</b>jkl</p>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ol><li><i>abc</i>def[]<b>ghi</b>jkl</li></ol>",
                });
            });

            test("should merge a paragraph starting with bold text into a list item with ending with italic text", async () => {
                await testEditor({
                    contentBefore: "<ol><li><b>abc</b><i>def</i></li></ol><p><b>[]ghi</b>jkl</p>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ol><li><b>abc</b><i>def[]</i><b>ghi</b>jkl</li></ol>",
                });
            });
        });
    });
    describe("Unordered", () => {
        describe("Basic", () => {
            test("should do nothing", async () => {
                await testEditor({
                    contentBefore: "<ul><li><br>[]</li></ul>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>[]<br></p>",
                });
                await testEditor({
                    contentBefore: '<ul><li class="oe-nested"><ul><li>[]abc</li></ul></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>[]abc</p>",
                });
            });

            test("should delete the first character in a list item", async () => {
                await testEditor({
                    contentBefore: "<ul><li>abc</li><li>d[]efg</li></ul>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ul><li>abc</li><li>[]efg</li></ul>",
                });
            });

            test("should delete a character within a list item", async () => {
                await testEditor({
                    contentBefore: "<ul><li>abc</li><li>de[]fg</li></ul>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ul><li>abc</li><li>d[]fg</li></ul>",
                });
            });

            test("should delete the last character in a list item", async () => {
                await testEditor({
                    contentBefore: "<ul><li>abc</li><li>defg[]</li></ul>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ul><li>abc</li><li>def[]</li></ul>",
                });
            });

            test("should remove the only character in a list", async () => {
                await testEditor({
                    contentBefore: "<ul><li>a[]</li></ul>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ul><li>[]<br></li></ul>",
                });
                await testEditor({
                    contentBefore: "<ul><li><p>a[]</p></li></ul>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ul><li><p>[]<br></p></li></ul>",
                });
            });

            test("should merge a list item with its previous list item", async () => {
                await testEditor({
                    contentBefore: "<ul><li>abc</li><li>[]def</li></ul>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ul><li>abc</li></ul><p>[]def</p>",
                });
                // With another list item after.
                await testEditor({
                    contentBefore: "<ul><li>abc</li><li>[]def</li><li>ghi</li></ul>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ul><li>abc</li></ul><p>[]def</p><ul><li>ghi</li></ul>",
                });
                // Where the list item to merge into is empty, with an
                // empty list item before.
                await testEditor({
                    contentBefore: "<ul><li><br></li><li><br></li><li>[]abc</li></ul>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ul><li><br></li><li><br></li></ul><p>[]abc</p>",
                });
            });

            test("should rejoin sibling lists (ul)", async () => {
                await testEditor({
                    contentBefore: "<ul><li>a</li></ul><p>[]b</p><ul><li>c</li></ul>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ul><li>a[]b</li><li>c</li></ul>",
                });
            });

            test("should rejoin multi-level sibling lists", async () => {
                await testEditor({
                    contentBefore: unformat(`
                            <ul>
                                <li><p>a</p>
                                    <ul>
                                        <li>b</li>
                                    </ul>
                                </li>
                            </ul>
                            <p>[]c</p>
                            <ul>
                                <li class="oe-nested">
                                    <ul>
                                        <li>d</li>
                                    </ul>
                                </li>
                                <li>e</li>
                            </ul>`),
                    stepFunction: deleteBackward,
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

            test("should only rejoin same-level lists", async () => {
                await testEditor({
                    contentBefore: unformat(`
                            <ul>
                                <li><p>a</p>
                                    <ul>
                                        <li>b</li>
                                    </ul>
                                </li>
                                <li>c</li>
                            </ul>
                            <p>[]d</p>
                            <ul>
                                <li class="oe-nested">
                                    <ul>
                                        <li>e</li>
                                    </ul>
                                </li>
                                <li>f</li>
                            </ul>`),
                    stepFunction: deleteBackward,
                    contentAfter: unformat(`
                            <ul>
                                <li><p>a</p>
                                    <ul>
                                        <li>b</li>
                                    </ul>
                                </li>
                                <li><p>c[]d</p>
                                    <ul>
                                        <li>e</li>
                                    </ul>
                                </li>
                                <li>f</li>
                            </ul>`),
                });
            });

            test("should not convert mixed lists on rejoin", async () => {
                await testEditor({
                    contentBefore: "<ul><li>a</li></ul><p>[]b</p><ol><li>c</li></ol>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ul><li>a[]b</li></ul><ol><li>c</li></ol>",
                });
            });

            test("should not convert mixed multi-level lists on rejoin", async () => {
                await testEditor({
                    contentBefore: unformat(`
                            <ul>
                                <li><p>a</p>
                                    <ol>
                                        <li>b</li>
                                    </ol>
                                </li>
                            </ul>
                            <p>[]c</p>
                            <ol>
                                <li class="oe-nested">
                                    <ul>
                                        <li>d</li>
                                    </ul>
                                </li>
                                <li>e</li>
                            </ol>`),
                    stepFunction: deleteBackward,
                    contentAfter: unformat(`
                            <ul>
                                <li><p>a</p>
                                    <ol>
                                        <li>b[]c</li>
                                    </ol>
                                </li>
                            </ul>
                            <ol>
                                <li class="oe-nested">
                                    <ul>
                                        <li>d</li>
                                    </ul>
                                </li>
                                <li>e</li>
                            </ol>`),
                });
            });
        });
        describe("Indented", () => {
            test("should merge an indented list item into a non-indented list item", async () => {
                await testEditor({
                    contentBefore: unformat(`
                            <ul>
                                <li><p>abc</p>
                                    <ul>
                                        <li>[]def</li>
                                        <li>ghi</li>
                                    </ul>
                                </li>
                            </ul>`),
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: unformat(`
                            <ul>
                                <li><p>abc[]def</p>
                                    <ul>
                                        <li>ghi</li>
                                    </ul>
                                </li>
                            </ul>`),
                });
            });

            test("should merge a non-indented list item into an indented list item", async () => {
                await testEditor({
                    contentBefore:
                        '<ul><li class="oe-nested"><ul><li>abc</li></ul></li><li>[]def</li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter:
                        '<ul><li class="oe-nested"><ul><li>abc</li></ul></li></ul><p>[]def</p>',
                });
            });

            test("should merge the only item in an indented list into a non-indented list item and remove the now empty indented list", async () => {
                await testEditor({
                    contentBefore: "<ul><li><p>abc</p><ul><li>[]def</li></ul></li></ul>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ul><li><p>abc[]def</p></li></ul>",
                });
            });

            test("should outdent a list item", async () => {
                await testEditor({
                    contentBefore: '<ul><li class="oe-nested"><ul><li>[]abc</li></ul></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>[]abc</p>",
                });
                // With a paragraph before the list:
                await testEditor({
                    contentBefore:
                        '<p>abc</p><ul><li class="oe-nested"><ul><li>[]def</li></ul></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>abc</p><p>[]def</p>",
                });
            });

            test("should outdent an empty list item within a list", async () => {
                await testEditor({
                    contentBefore:
                        "<ul><li><p>abc</p><ul><li>[]<br></li><li><br></li></ul></li><li>def</li></ul>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter:
                        '<ul><li><p>abc</p></li></ul><p>[]<br></p><ul><li class="oe-nested"><ul><li><br></li></ul></li><li>def</li></ul>',
                });
            });

            test("should outdent an empty list within a list", async () => {
                await testEditor({
                    contentBefore:
                        "<ul><li><p>abc</p><ul><li>[]<br></li></ul></li><li>def</li></ul>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ul><li><p>abc</p></li></ul><p>[]<br></p><ul><li>def</li></ul>",
                });
            });

            test("should outdent an empty list", async () => {
                await testEditor({
                    contentBefore: '<ul><li class="oe-nested"><ul><li><br>[]</li></ul></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>[]<br></p>",
                });
            });

            test("should outdent a list to the point that it's a paragraph", async () => {
                await testEditor({
                    contentBefore: "<ul><li>[]<br></li></ul>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>[]<br></p>",
                });
                // With a paragraph before the list:
                await testEditor({
                    contentBefore: "<p><br></p><ul><li>[]<br></li></ul>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p><br></p><p>[]<br></p>",
                });
            });
        });
        describe("Complex merges", () => {
            test("should merge a list item into a paragraph", async () => {
                await testEditor({
                    contentBefore: "<p>abcd</p><ul><li>ef[]gh</li><li>ij</li></ul>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>abcd[]gh</p><ul><li>ij</li></ul>",
                });
            });

            test("should merge a paragraph into a list item", async () => {
                await testEditor({
                    contentBefore: "<ul><li>abc</li></ul><p>[]def</p>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ul><li>abc[]def</li></ul>",
                });
            });

            test("should not merge a bold list item into a non-formatted list item", async () => {
                await testEditor({
                    contentBefore:
                        "<ul>" +
                        "<li>abc</li>" +
                        "<li><b>de</b>fg</li>" +
                        "<li><b>[]hij</b>klm</li>" +
                        "<li>nop</li>" +
                        "</ul>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter:
                        "<ul>" +
                        "<li>abc</li>" +
                        "<li><b>de</b>fg</li>" +
                        "</ul>" +
                        "<p><b>[]hij</b>klm</p>" +
                        "<ul>" +
                        "<li>nop</li>" +
                        "</ul>",
                });
            });

            test("should merge a paragraph starting with bold text into a list item with ending without formatting", async () => {
                await testEditor({
                    contentBefore: "<ul><li><i>abc</i>def</li></ul><p><b>[]ghi</b>jkl</p>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ul><li><i>abc</i>def[]<b>ghi</b>jkl</li></ul>",
                });
            });

            test("should merge a paragraph starting with bold text into a list item with ending with italic text", async () => {
                await testEditor({
                    contentBefore: "<ul><li><b>abc</b><i>def</i></li></ul><p><b>[]ghi</b>jkl</p>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ul><li><b>abc</b><i>def[]</i><b>ghi</b>jkl</li></ul>",
                });
            });
        });
    });
    describe("Checklist", () => {
        describe("Basic", () => {
            test("should remove the list and turn into p", async () => {
                await testEditor({
                    contentBefore: '<ul class="o_checklist"><li><br>[]</li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>[]<br></p>",
                });
                await testEditor({
                    contentBefore: '<ul class="o_checklist"><li class="o_checked"><br>[]</li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>[]<br></p>",
                });
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">[]abc</li></ul></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>[]abc</p>",
                });
            });

            test("should delete the first character in a list item", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li class="o_checked">abc</li><li class="o_checked">d[]efg</li></ul>',
                    stepFunction: deleteBackward,
                    contentAfter:
                        '<ul class="o_checklist"><li class="o_checked">abc</li><li class="o_checked">[]efg</li></ul>',
                });
            });

            test("should delete a character within a list item", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li class="o_checked">abc</li><li class="o_checked">de[]fg</li></ul>',
                    stepFunction: deleteBackward,
                    contentAfter:
                        '<ul class="o_checklist"><li class="o_checked">abc</li><li class="o_checked">d[]fg</li></ul>',
                });
            });

            test("should delete the last character in a list item", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li class="o_checked">abc</li><li class="o_checked">defg[]</li></ul>',
                    stepFunction: deleteBackward,
                    contentAfter:
                        '<ul class="o_checklist"><li class="o_checked">abc</li><li class="o_checked">def[]</li></ul>',
                });
            });

            test("should remove the only character in a list", async () => {
                await testEditor({
                    contentBefore: '<ul class="o_checklist"><li class="o_checked">a[]</li></ul>',
                    stepFunction: deleteBackward,
                    // keep checked because contains the paragraph
                    contentAfter: '<ul class="o_checklist"><li class="o_checked">[]<br></li></ul>',
                });
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li class="o_checked"><p>a[]</p></li></ul>',
                    stepFunction: deleteBackward,
                    contentAfter:
                        '<ul class="o_checklist"><li class="o_checked"><p>[]<br></p></li></ul>',
                });
            });

            test("should remove the checkmark when the list item marker is deleted", async () => {
                await testEditor({
                    contentBefore: '<ul class="o_checklist"><li class="o_checked">[]</li></ul>',
                    stepFunction: deleteBackward,
                    contentAfter: '<ul class="o_checklist"><li class="oe-nested">[]</li></ul>',
                });
            });

            describe("should merge a list item with its previous list item", () => {
                test("should merge a list item with its previous list item (1)", async () => {
                    await testEditor({
                        contentBefore:
                            '<ul class="o_checklist"><li class="o_checked">abc</li><li class="o_checked">[]def</li></ul>',
                        stepFunction: async (editor) => {
                            deleteBackward(editor);
                            deleteBackward(editor);
                        },
                        contentAfter:
                            '<ul class="o_checklist"><li class="o_checked">abc</li></ul><p>[]def</p>',
                    });
                });
                test("should merge a list item with its previous list item (2)", async () => {
                    await testEditor({
                        contentBefore:
                            '<ul class="o_checklist"><li class="o_checked">abc</li><li>[]def</li></ul>',
                        stepFunction: async (editor) => {
                            deleteBackward(editor);
                            deleteBackward(editor);
                        },
                        contentAfter:
                            '<ul class="o_checklist"><li class="o_checked">abc</li></ul><p>[]def</p>',
                    });
                });
                test("should merge a list item with its previous list item (3)", async () => {
                    await testEditor({
                        contentBefore:
                            '<ul class="o_checklist"><li>abc</li><li class="o_checked">[]def</li></ul>',
                        stepFunction: async (editor) => {
                            deleteBackward(editor);
                            deleteBackward(editor);
                        },
                        contentAfter: '<ul class="o_checklist"><li>abc</li></ul><p>[]def</p>',
                    });
                });
                test("should merge a list item with its previous list item (4)", async () => {
                    // With another list item after.
                    await testEditor({
                        contentBefore:
                            '<ul class="o_checklist"><li class="o_checked">abc</li><li class="o_checked">[]def</li><li class="o_checked">ghi</li></ul>',
                        stepFunction: async (editor) => {
                            deleteBackward(editor);
                            deleteBackward(editor);
                        },
                        contentAfter:
                            '<ul class="o_checklist"><li class="o_checked">abc</li></ul><p>[]def</p><ul class="o_checklist"><li class="o_checked">ghi</li></ul>',
                    });
                });
                test("should merge a list item with its previous list item (5)", async () => {
                    await testEditor({
                        contentBefore:
                            '<ul class="o_checklist"><li class="o_checked">abc</li><li>[]def</li><li>ghi</li></ul>',
                        stepFunction: async (editor) => {
                            deleteBackward(editor);
                            deleteBackward(editor);
                        },
                        contentAfter:
                            '<ul class="o_checklist"><li class="o_checked">abc</li></ul><p>[]def</p><ul class="o_checklist"><li>ghi</li></ul>',
                    });
                });
                test("should merge a list item with its previous list item (6)", async () => {
                    await testEditor({
                        contentBefore:
                            '<ul class="o_checklist"><li class="o_checked">abc</li><li>[]def</li><li class="o_checked">ghi</li></ul>',
                        stepFunction: async (editor) => {
                            deleteBackward(editor);
                            deleteBackward(editor);
                        },
                        contentAfter:
                            '<ul class="o_checklist"><li class="o_checked">abc</li></ul><p>[]def</p><ul class="o_checklist"><li class="o_checked">ghi</li></ul>',
                    });
                });
                test("should merge a list item with its previous list item (7)", async () => {
                    // Where the list item to merge into is empty, with an
                    // empty list item before.
                    await testEditor({
                        contentBefore:
                            '<ul class="o_checklist"><li><br></li><li><br></li><li class="o_checked">[]abc</li></ul>',
                        stepFunction: async (editor) => {
                            deleteBackward(editor);
                            deleteBackward(editor);
                        },
                        contentAfter:
                            '<ul class="o_checklist"><li><br></li><li><br></li></ul><p>[]abc</p>',
                    });
                });
            });

            test("should rejoin sibling lists (cl)", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li class="o_checked">a</li></ul><p>[]b</p><ul class="o_checklist"><li class="o_checked">c</li></ul>',
                    stepFunction: deleteBackward,
                    contentAfter:
                        '<ul class="o_checklist"><li class="o_checked">a[]b</li><li class="o_checked">c</li></ul>',
                });
            });

            test("should rejoin multi-level sibling lists", async () => {
                await testEditor({
                    contentBefore: unformat(`
                            <ul class="o_checklist">
                                <li><p>a</p>
                                    <ul class="o_checklist">
                                        <li class="o_checked">b</li>
                                    </ul>
                                </li>
                            </ul>
                            <p>[]c</p>
                            <ul class="o_checklist">
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li class="o_checked">d</li>
                                    </ul>
                                </li>
                                <li class="o_checked">e</li>
                            </ul>`),
                    stepFunction: deleteBackward,
                    contentAfter: unformat(`
                            <ul class="o_checklist">
                                <li><p>a</p>
                                    <ul class="o_checklist">
                                        <li class="o_checked">b[]c</li>
                                        <li class="o_checked">d</li>
                                    </ul>
                                </li>
                                <li class="o_checked">e</li>
                            </ul>`),
                });
                await testEditor({
                    contentBefore: unformat(`
                            <ul class="o_checklist">
                                <li><p>a</p>
                                    <ul class="o_checklist">
                                        <li class="o_checked">b</li>
                                    </ul>
                                </li>
                            </ul>
                            <p>[]c</p>
                            <ul class="o_checklist">
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li>d</li>
                                    </ul>
                                </li>
                                <li class="o_checked">e</li>
                            </ul>`),
                    stepFunction: deleteBackward,
                    contentAfter: unformat(`
                            <ul class="o_checklist">
                                <li><p>a</p>
                                    <ul class="o_checklist">
                                        <li class="o_checked">b[]c</li>
                                        <li>d</li>
                                    </ul>
                                </li>
                                <li class="o_checked">e</li>
                            </ul>`),
                });
            });

            test("should only rejoin same-level lists", async () => {
                await testEditor({
                    contentBefore: unformat(`
                            <ul class="o_checklist">
                                <li><p>a</p>
                                    <ul class="o_checklist">
                                        <li class="o_checked">b</li>
                                    </ul>
                                </li>
                                <li class="o_checked">c</li>
                            </ul>
                            <p>[]d</p>
                            <ul class="o_checklist">
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li class="o_checked">e</li>
                                    </ul>
                                </li>
                                <li class="o_checked">f</li>
                            </ul>`),
                    stepFunction: deleteBackward,
                    contentAfter: unformat(`
                            <ul class="o_checklist">
                                <li><p>a</p>
                                    <ul class="o_checklist">
                                        <li class="o_checked">b</li>
                                    </ul>
                                </li>
                                <li class="o_checked"><p>c[]d</p>
                                    <ul class="o_checklist">
                                        <li class="o_checked">e</li>
                                    </ul>
                                </li>
                                <li class="o_checked">f</li>
                            </ul>`),
                });
                await testEditor({
                    contentBefore: unformat(`
                            <ul class="o_checklist">
                                <li><p>a</p>
                                    <ul class="o_checklist">
                                        <li class="o_checked">b</li>
                                    </ul>
                                </li>
                                <li>c</li>
                            </ul>
                            <p>[]d</p>
                            <ul class="o_checklist">
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li class="o_checked">e</li>
                                    </ul>
                                </li>
                                <li class="o_checked">f</li>
                            </ul>`),
                    stepFunction: deleteBackward,
                    contentAfter: unformat(`
                            <ul class="o_checklist">
                                <li><p>a</p>
                                    <ul class="o_checklist">
                                        <li class="o_checked">b</li>
                                    </ul>
                                </li>
                                <li><p>c[]d</p>
                                    <ul class="o_checklist">
                                        <li class="o_checked">e</li>
                                    </ul>
                                </li>
                                <li class="o_checked">f</li>
                            </ul>`),
                });
            });

            test("should not convert mixed lists on rejoin", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li class="o_checked">a</li></ul><p>[]b</p><ul><li>c</li></ul>',
                    stepFunction: deleteBackward,
                    contentAfter:
                        '<ul class="o_checklist"><li class="o_checked">a[]b</li></ul><ul><li>c</li></ul>',
                });
            });

            test("should not convert mixed multi-level lists on rejoin", async () => {
                await testEditor({
                    contentBefore: unformat(`
                            <ul class="o_checklist">
                                <li><p>a</p>
                                    <ul>
                                        <li>b</li>
                                    </ul>
                                </li>
                            </ul>
                            <p>[]c</p>
                            <ul>
                                <li class="oe-nested">
                                    <ul>
                                        <li>d</li>
                                    </ul>
                                </li>
                                <li>e</li>
                            </ul>`),
                    stepFunction: deleteBackward,
                    contentAfter: unformat(`
                            <ul class="o_checklist">
                                <li><p>a</p>
                                    <ul>
                                        <li>b[]c</li>
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
            test("should merge an indented list item into a non-indented list item", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li><p>abc</p><ul class="o_checklist"><li class="o_checked">[]def</li><li class="o_checked">ghi</li></ul></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter:
                        '<ul class="o_checklist"><li><p>abc[]def</p><ul class="o_checklist"><li class="o_checked">ghi</li></ul></li></ul>',
                });
            });

            test("should merge a non-indented list item into an indented list item", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">abc</li></ul></li><li class="o_checked">[]def</li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter:
                        '<ul class="o_checklist"><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">abc</li></ul></li></ul><p>[]def</p>',
                });
            });

            test("should merge the only item in an indented list into a non-indented list item and remove the now empty indented list", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li><p>abc</p><ul class="o_checklist"><li class="o_checked">[]def</li></ul></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: '<ul class="o_checklist"><li><p>abc[]def</p></li></ul>',
                });
            });

            test("should outdent a list item", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">[]abc</li></ul></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>[]abc</p>",
                });
                // With a paragraph before the list:
                await testEditor({
                    contentBefore:
                        '<p>abc</p><ul class="o_checklist"><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">[]def</li></ul></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>abc</p><p>[]def</p>",
                });
            });

            test("should outdent the list item without removing the header tag", async () => {
                await testEditor({
                    contentBefore:
                        "<ul>" +
                        "<li>abc" +
                        "<ul>" +
                        "<li><h1>[]def</h1></li>" +
                        "</ul></li>" +
                        "</ul>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ul>" + "<li><p>abc</p></li>" + "</ul>" + "<h1>[]def</h1>",
                });
            });

            test.skip("should outdent while nested within a list item", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li class="o_checked"><div>abc</div></li><li class="o_checked"><div><div>[]def</div></div></li></ul>',
                    stepFunction: deleteBackward,
                    // TODO: the additional DIV used to represent
                    // the LI. The ideal result would be:
                    // contentAfter: '<ul class="o_checklist"><li class="o_checked"><div>abc</div></li></ul><div><div>[]def</div></div>',
                    contentAfter:
                        '<ul class="o_checklist"><li class="o_checked"><div>abc</div></li></ul><div><div><div>[]def</div></div></div>',
                });
                // With a div before the list:
                await testEditor({
                    contentBefore:
                        '<div>abc</div><ul class="o_checklist"><li class="o_checked"><div><div>[]def</div></div></li></ul>',
                    stepFunction: deleteBackward,
                    // TODO: the additional DIV used to represent
                    // the LI. The ideal result would be:
                    // contentAfter: '<div>abc</div><div><div>[]def</div></div>',
                    contentAfter: "<div>abc</div><div><div><div>[]def</div></div></div>",
                });
            });

            test("should outdent an empty list item within a list", async () => {
                await testEditor({
                    contentBefore: unformat(`
                            <ul class="o_checklist">
                                <li><p>abc</p>
                                    <ul class="o_checklist">
                                        <li>[]<br></li>
                                        <li><br></li>
                                    </ul>
                                </li>
                                <li class="o_checked">def</li>
                            </ul>`),
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: unformat(`
                            <ul class="o_checklist">
                                <li><p>abc</p></li>
                            </ul>
                            <p>[]<br></p>
                            <ul class="o_checklist">
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li><br></li>
                                    </ul>
                                </li>
                                <li class="o_checked">def</li>
                            </ul>`),
                });
            });

            test("should outdent an empty list within a list", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li><p>abc</p><ul class="o_checklist"><li>[]<br></li></ul></li><li class="o_checked">def</li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter:
                        '<ul class="o_checklist"><li><p>abc</p></li></ul><p>[]<br></p><ul class="o_checklist"><li class="o_checked">def</li></ul>',
                });
            });

            test("should outdent an empty list", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li class="oe-nested"><ul class="o_checklist"><li class="o_checked"><br>[]</li></ul></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>[]<br></p>",
                });
            });

            test("should outdent a list to the point that it's a paragraph", async () => {
                await testEditor({
                    contentBefore: '<ul class="o_checklist"><li>[]<br></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>[]<br></p>",
                });
                // With a paragraph before the list:
                await testEditor({
                    contentBefore: '<p><br></p><ul class="o_checklist"><li>[]<br></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p><br></p><p>[]<br></p>",
                });
            });
        });
        describe("Complex merges", () => {
            test("should merge a list item into a paragraph", async () => {
                await testEditor({
                    contentBefore:
                        '<p>abcd</p><ul class="o_checklist"><li class="o_checked">ef[]gh</li><li class="o_checked">ij</li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter:
                        '<p>abcd[]gh</p><ul class="o_checklist"><li class="o_checked">ij</li></ul>',
                });
                await testEditor({
                    contentBefore:
                        '<p>abcd</p><ul class="o_checklist"><li>ef[]gh</li><li class="o_checked">ij</li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter:
                        '<p>abc[]gh</p><ul class="o_checklist"><li class="o_checked">ij</li></ul>',
                });
                await testEditor({
                    contentBefore:
                        '<p>abcd</p><ul class="o_checklist"><li class="o_checked">ef[]gh</li><li>ij</li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: '<p>abc[]gh</p><ul class="o_checklist"><li>ij</li></ul>',
                });
            });

            test("should merge a paragraph into a list item", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li class="o_checked">abc</li></ul><p>[]def</p>',
                    stepFunction: deleteBackward,
                    contentAfter:
                        '<ul class="o_checklist"><li class="o_checked">abc[]def</li></ul>',
                });
            });

            test("should merge a bold list item into a non-formatted list item", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist">' +
                        '<li class="o_checked">abc</li>' +
                        '<li class="o_checked"><b>de</b>fg</li>' +
                        '<li class="o_checked"><b>[]hij</b>klm</li>' +
                        '<li class="o_checked">nop</li>' +
                        "</ul>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter:
                        '<ul class="o_checklist">' +
                        '<li class="o_checked">abc</li>' +
                        '<li class="o_checked"><b>de</b>fg</li>' +
                        "</ul>" +
                        "<p><b>[]hij</b>klm</p>" +
                        '<ul class="o_checklist">' +
                        '<li class="o_checked">nop</li>' +
                        "</ul>",
                });
            });

            test("should merge a paragraph starting with bold text into a list item with ending without formatting", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li class="o_checked"><i>abc</i>def</li></ul><p><b>[]ghi</b>jkl</p>',
                    stepFunction: deleteBackward,
                    contentAfter:
                        '<ul class="o_checklist"><li class="o_checked"><i>abc</i>def[]<b>ghi</b>jkl</li></ul>',
                });
            });

            test("should merge a paragraph starting with bold text into a list item with ending with italic text", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li class="o_checked"><b>abc</b><i>def</i></li></ul><p><b>[]ghi</b>jkl</p>',
                    stepFunction: deleteBackward,
                    contentAfter:
                        '<ul class="o_checklist"><li class="o_checked"><b>abc</b><i>def[]</i><b>ghi</b>jkl</li></ul>',
                });
            });
        });
    });
    describe("Mixed", () => {
        describe("Ordered to unordered", () => {
            test("should merge an ordered list into an unordered list (1)", async () => {
                await testEditor({
                    contentBefore: "<ul><li>a</li></ul><ol><li>[]b</li></ol>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ul><li>a[]b</li></ul>",
                });
            });
            test("should merge an ordered list into an unordered list (2)", async () => {
                await testEditor({
                    contentBefore: "<ul><li>a</li></ul><ol><li><p>[]b</p></li></ol>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ul><li>a[]b</li></ul>",
                });
            });
            test("should merge an ordered list into an unordered list (3)", async () => {
                await testEditor({
                    contentBefore: "<ul><li><p>a</p></li></ul><ol><li>[]b</li></ol>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ul><li><p>a[]b</p></li></ul>",
                });
            });
            test("should merge an ordered list into an unordered list (4)", async () => {
                await testEditor({
                    contentBefore: "<ul><li><p>a</p></li></ul><ol><li><p>[]b</p></li></ol>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ul><li><p>a[]b</p></li></ul>",
                });
            });

            test("should merge an ordered list item that is in an unordered list item into a non-indented list item", async () => {
                await testEditor({
                    contentBefore:
                        "<ul><li><p>abc</p><ol><li>[]def</li><li>ghi</li></ol></li></ul>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter:
                        '<ul><li><p>abc</p></li></ul><p>[]def</p><ul><li class="oe-nested"><ol><li>ghi</li></ol></li></ul>',
                });
            });

            test("should merge an ordered list item into an unordered list item that is in the same ordered list", async () => {
                await testEditor({
                    contentBefore:
                        '<ol><li class="oe-nested"><ul><li>abc</li></ul></li><li>[]def</li></ol>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter:
                        '<ol><li class="oe-nested"><ul><li>abc</li></ul></li></ol><p>[]def</p>',
                });
            });

            test("should merge the only item in an ordered list that is in an unordered list into a list item that is in the same unordered list, and remove the now empty ordered list", async () => {
                await testEditor({
                    contentBefore: "<ul><li><p>abc</p><ol><li>[]def</li></ol></li></ul>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ul><li><p>abc[]def</p></li></ul>",
                });
            });

            test("should outdent an ordered list item that is within a unordered list", async () => {
                await testEditor({
                    contentBefore: '<ul><li class="oe-nested"><ol><li>[]abc</li></ol></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>[]abc</p>",
                });
                // With a paragraph before the list:
                await testEditor({
                    contentBefore:
                        '<p>abc</p><ul><li class="oe-nested"><ol><li>[]def</li></ol></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>abc</p><p>[]def</p>",
                });
            });

            test("should outdent an empty ordered list item within an unordered list", async () => {
                await testEditor({
                    contentBefore:
                        "<ul><li><p>abc</p><ol><li>[]<br></li><li><br></li></ol></li><li>def</li></ul>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter:
                        '<ul><li><p>abc</p></li></ul><p>[]<br></p><ul><li class="oe-nested"><ol><li><br></li></ol></li><li>def</li></ul>',
                });
            });

            test("should outdent an empty ordered list within an unordered list", async () => {
                await testEditor({
                    contentBefore:
                        "<ul><li><p>abc</p><ol><li>[]<br></li></ol></li><li>def</li></ul>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ul><li><p>abc</p></li></ul><p>[]<br></p><ul><li>def</li></ul>",
                });
            });

            test("should outdent an empty ordered list within an unordered list (2)", async () => {
                await testEditor({
                    contentBefore: '<ul><li class="oe-nested"><ol><li><br>[]</li></ol></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>[]<br></p>",
                });
            });
        });
        describe("Unordered to ordered", () => {
            test("should merge an unordered list into an ordered list", async () => {
                await testEditor({
                    contentBefore: "<ol><li>a</li></ol><ul><li>[]b</li></ul>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ol><li>a[]b</li></ol>",
                });
                await testEditor({
                    contentBefore: "<ol><li>a</li></ol><ul><li><p>[]b</p></li></ul>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ol><li>a[]b</li></ol>",
                });
                await testEditor({
                    contentBefore: "<ol><li><p>a</p></li></ol><ul><li>[]b</li></ul>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ol><li><p>a[]b</p></li></ol>",
                });
                await testEditor({
                    contentBefore: "<ol><li><p>a</p></li></ol><ul><li><p>[]b</p></li></ul>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ol><li><p>a[]b</p></li></ol>",
                });
            });

            test("should merge an unordered list item that is in an ordered list item into a non-indented list item", async () => {
                await testEditor({
                    contentBefore: unformat(`
                            <ol>
                                <li><p>abc</p>
                                    <ul>
                                        <li>[]def</li>
                                        <li>ghi</li>
                                    </ul>
                                </li>
                            </ol>`),
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: unformat(`
                            <ol>
                                <li><p>abc</p></li>
                            </ol>
                            <p>[]def</p>
                            <ol>
                                <li class="oe-nested">
                                    <ul>
                                        <li>ghi</li>
                                    </ul>
                                </li>
                            </ol>`),
                });
            });

            test("should merge an unordered list item into an ordered list item that is in the same unordered list", async () => {
                await testEditor({
                    contentBefore:
                        '<ul><li class="oe-nested"><ol><li>abc</li></ol></li><li>[]def</li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter:
                        '<ul><li class="oe-nested"><ol><li>abc</li></ol></li></ul><p>[]def</p>',
                });
            });

            test("should merge the only item in an unordered list that is in an ordered list into a list item that is in the same ordered list, and remove the now empty unordered list", async () => {
                await testEditor({
                    contentBefore: "<ol><li><p>abc</p><ul><li>[]def</li></ul></li></ol>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ol><li><p>abc[]def</p></li></ol>",
                });
            });

            test("should outdent an unordered list item that is within a ordered list", async () => {
                await testEditor({
                    contentBefore: '<ol><li class="oe-nested"><ul><li>[]abc</li></ul></li></ol>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>[]abc</p>",
                });
                // With a paragraph before the list:
                await testEditor({
                    contentBefore:
                        '<p>abc</p><ol><li class="oe-nested"><ul><li>[]def</li></ul></li></ol>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>abc</p><p>[]def</p>",
                });
            });

            test("should outdent an empty unordered list item within an ordered list", async () => {
                await testEditor({
                    contentBefore:
                        "<ol><li><p>abc</p><ul><li>[]<br></li><li><br></li></ul></li><li>def</li></ol>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter:
                        '<ol><li><p>abc</p></li></ol><p>[]<br></p><ol><li class="oe-nested"><ul><li><br></li></ul></li><li>def</li></ol>',
                });
            });

            test("should outdent an empty unordered list within an ordered list", async () => {
                await testEditor({
                    contentBefore:
                        "<ol><li><p>abc</p><ul><li>[]<br></li></ul></li><li>def</li></ol>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ol><li><p>abc</p></li></ol><p>[]<br></p><ol><li>def</li></ol>",
                });
            });

            test("should outdent an empty unordered list within an ordered list (2)", async () => {
                await testEditor({
                    contentBefore: '<ol><li class="oe-nested"><ul><li><br>[]</li></ul></li></ol>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>[]<br></p>",
                });
            });
        });
        describe("Checklist to unordered", () => {
            test("should merge an checklist list into an unordered list (1)", async () => {
                await testEditor({
                    contentBefore: '<ul><li>a</li></ul><ul class="o_checklist"><li>[]b</li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ul><li>a[]b</li></ul>",
                });
            });
            test("should merge an checklist list into an unordered list (2)", async () => {
                await testEditor({
                    contentBefore:
                        '<ul><li>a</li></ul><ul class="o_checklist"><li><p>[]b</p></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ul><li>a[]b</li></ul>",
                });
            });
            test("should merge an checklist list into an unordered list (3)", async () => {
                await testEditor({
                    contentBefore:
                        '<ul><li><p>a</p></li></ul><ul class="o_checklist"><li>[]b</li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ul><li><p>a[]b</p></li></ul>",
                });
            });
            test("should merge an checklist list into an unordered list (4)", async () => {
                await testEditor({
                    contentBefore:
                        '<ul><li><p>a</p></li></ul><ul class="o_checklist"><li><p>[]b</p></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ul><li><p>a[]b</p></li></ul>",
                });
            });

            test("should merge an checklist list item that is in an unordered list item into a non-indented list item", async () => {
                await testEditor({
                    contentBefore:
                        '<ul><li><p>abc</p><ul class="o_checklist"><li class="o_checked">[]def</li><li class="o_checked">ghi</li></ul></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter:
                        '<ul><li><p>abc[]def</p><ul class="o_checklist"><li class="o_checked">ghi</li></ul></li></ul>',
                });
            });

            test("should merge an checklist list item into an unordered list item that is in the same checklist list", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li class="oe-nested"><ul><li>abc</li></ul></li><li>[]def</li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter:
                        '<ul class="o_checklist"><li class="oe-nested"><ul><li>abc</li></ul></li></ul><p>[]def</p>',
                });
            });

            test("should merge the only item in an checklist list that is in an unordered list into a checklist item that is in the same unordered list, and remove the now empty checklist list", async () => {
                await testEditor({
                    contentBefore:
                        '<ul><li><p>abc</p><ul class="o_checklist"><li class="o_checked">[]def</li></ul></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ul><li><p>abc[]def</p></li></ul>",
                });
            });

            test("should outdent an checklist list item that is within a unordered list", async () => {
                await testEditor({
                    contentBefore:
                        '<ul><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">[]abc</li></ul></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>[]abc</p>",
                });
                // With a paragraph before the list:
                await testEditor({
                    contentBefore:
                        '<p>abc</p><ul><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">[]def</li></ul></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>abc</p><p>[]def</p>",
                });
            });

            test("should outdent an empty checklist list item within an unordered list", async () => {
                await testEditor({
                    contentBefore:
                        '<ul><li><p>abc</p><ul class="o_checklist"><li>[]<br></li><li><br></li></ul></li><li>def</li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter:
                        '<ul><li><p>abc</p></li></ul><p>[]<br></p><ul><li class="oe-nested"><ul class="o_checklist"><li><br></li></ul></li><li>def</li></ul>',
                });
            });

            test("should outdent an empty checklist list within an unordered list", async () => {
                await testEditor({
                    contentBefore:
                        '<ul><li><p>abc</p><ul class="o_checklist"><li>[]<br></li></ul></li><li>def</li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<ul><li><p>abc</p></li></ul><p>[]<br></p><ul><li>def</li></ul>",
                });
            });

            test("should outdent an empty checklist list within an unordered list (2)", async () => {
                await testEditor({
                    contentBefore:
                        '<ul><li class="oe-nested"><ul class="o_checklist"><li><br>[]</li></ul></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>[]<br></p>",
                });
            });
        });
        describe("Unordered to checklist", () => {
            test("should merge an unordered list into an checklist list", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li class="o_checked">a</li></ul><ul><li>[]b</li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: '<ul class="o_checklist"><li class="o_checked">a[]b</li></ul>',
                });
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li class="o_checked">a</li></ul><ul><li><p>[]b</p></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    // Paragraphs in list items are treated as nonsense.
                    contentAfter: '<ul class="o_checklist"><li class="o_checked">a[]b</li></ul>',
                });
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li class="o_checked"><p>a</p></li></ul><ul><li>[]b</li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    // Paragraphs in list items are kept unless empty
                    contentAfter:
                        '<ul class="o_checklist"><li class="o_checked"><p>a[]b</p></li></ul>',
                });
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li class="o_checked"><p>a</p></li></ul><ul><li><p>[]b</p></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    // Paragraphs in list items are kept unless empty
                    contentAfter:
                        '<ul class="o_checklist"><li class="o_checked"><p>a[]b</p></li></ul>',
                });
            });

            test("should merge an unordered list item that is in an checklist list item into a non-indented list item", async () => {
                await testEditor({
                    contentBefore: unformat(`
                            <ul class="o_checklist">
                                <li><p>abc</p>
                                    <ul>
                                        <li>[]def</li>
                                        <li>ghi</li>
                                    </ul>
                                </li>
                            </ul>`),
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: unformat(`
                            <ul class="o_checklist">
                                <li><p>abc[]def</p>
                                    <ul>
                                        <li>ghi</li>
                                    </ul>
                                </li>
                            </ul>`),
                });
            });

            test("should merge an unordered list item into an checklist list item that is in the same unordered list", async () => {
                await testEditor({
                    contentBefore:
                        '<ul><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">abc</li></ul></li><li>[]def</li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter:
                        '<ul><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">abc</li></ul></li></ul><p>[]def</p>',
                });
            });

            test("should merge the only item in an unordered list that is in an checklist list into a checklist item that is in the same checklist list, and remove the now empty unordered list", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li><p>abc</p><ul><li>[]def</li></ul></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: '<ul class="o_checklist"><li><p>abc[]def</p></li></ul>',
                });
            });

            test("should outdent an unordered list item that is within a checklist list", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li class="oe-nested"><ul><li>[]abc</li></ul></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>[]abc</p>",
                });
                // With a paragraph before the list:
                await testEditor({
                    contentBefore:
                        '<p>abc</p><ul class="o_checklist"><li class="oe-nested"><ul><li>[]def</li></ul></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>abc</p><p>[]def</p>",
                });
            });

            test("should outdent an empty unordered list item within an checklist list (o_checked)", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li><p>abc</p><ul><li>[]<br></li><li><br></li></ul></li><li class="o_checked">def</li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter:
                        '<ul class="o_checklist"><li><p>abc</p></li></ul><p>[]<br></p><ul class="o_checklist"><li class="oe-nested"><ul><li><br></li></ul></li><li class="o_checked">def</li></ul>',
                });
            });

            test("should outdent an empty unordered list item within an checklist list (unchecked)", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li><p>abc</p><ul><li>[]<br></li><li><br></li></ul></li><li>def</li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter:
                        '<ul class="o_checklist"><li><p>abc</p></li></ul><p>[]<br></p><ul class="o_checklist"><li class="oe-nested"><ul><li><br></li></ul></li><li>def</li></ul>',
                });
            });

            test("should outdent an empty unordered list within an checklist list (checked)", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li><p>abc</p><ul><li>[]<br></li></ul></li><li class="o_checked">def</li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter:
                        '<ul class="o_checklist"><li><p>abc</p></li></ul><p>[]<br></p><ul class="o_checklist"><li class="o_checked">def</li></ul>',
                });
            });

            test("should outdent an empty unordered list within an checklist list (unchecked)", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li><p>abc</p><ul><li>[]<br></li></ul></li><li>def</li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter:
                        '<ul class="o_checklist"><li><p>abc</p></li></ul><p>[]<br></p><ul class="o_checklist"><li>def</li></ul>',
                });
            });

            test("should outdent an empty unordered list within an otherwise empty checklist list", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li class="oe-nested"><ul><li><br>[]</li></ul></li></ul>',
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>[]<br></p>",
                });
            });
        });
    });
    describe("Complex merges with some containers parsed in list item", () => {
        test("should treat two blocks in a list item and keep blocks", async () => {
            await testEditor({
                contentBefore:
                    "<ol><li><h1>abc</h1></li><li><h2>def</h2><h3>[]ghi</h3></li><li><h4>klm</h4></li></ol>",
                stepFunction: deleteBackward,
                // Paragraphs in list items are treated as nonsense.
                // Headings aren't, as they do provide extra information.
                contentAfter:
                    "<ol><li><h1>abc</h1></li><li><h2>def[]ghi</h2></li><li><h4>klm</h4></li></ol>",
            });
        });

        test("should treat two blocks in a list item and keep blocks (2)", async () => {
            await testEditor({
                contentBefore:
                    "<ul><li><h1>abc</h1></li><li><h2>def</h2><h3>[]ghi</h3></li><li><h4>klm</h4></li></ul>",
                stepFunction: deleteBackward,
                // Paragraphs in list items are treated as nonsense.
                // Headings aren't, as they do provide extra information.
                contentAfter:
                    "<ul><li><h1>abc</h1></li><li><h2>def[]ghi</h2></li><li><h4>klm</h4></li></ul>",
            });
        });

        test("should treat two blocks in a list item and keep blocks (3)", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li class="o_checked"><h1>abc</h1></li><li class="o_checked"><h2>def</h2><h3>[]ghi</h3></li><li class="o_checked"><h4>klm</h4></li></ul>',
                stepFunction: deleteBackward,
                // Paragraphs in list items are treated as nonsense.
                // Headings aren't, as they do provide extra information.
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
                stepFunction: deleteBackward,
                contentAfter: "<ol><li>ab[]ef</li></ol>",
            });
            // Backward selection
            await testEditor({
                contentBefore: "<ol><li>ab]cd[ef</li></ol>",
                stepFunction: deleteBackward,
                contentAfter: "<ol><li>ab[]ef</li></ol>",
            });
        });

        test("should delete all the text in a list item", async () => {
            // Forward selection
            await testEditor({
                contentBefore: "<ol><li>[abc]</li></ol>",
                stepFunction: deleteBackward,
                contentAfter: "<ol><li>[]<br></li></ol>",
            });
            // Backward selection
            await testEditor({
                contentBefore: "<ol><li>]abc[</li></ol>",
                stepFunction: deleteBackward,
                contentAfter: "<ol><li>[]<br></li></ol>",
            });
        });

        test("should delete across two list items", async () => {
            // Forward selection
            await testEditor({
                contentBefore: "<ol><li>ab[cd</li><li>ef]gh</li></ol>",
                stepFunction: deleteBackward,
                contentAfter: "<ol><li>ab[]gh</li></ol>",
            });
            // Backward selection
            await testEditor({
                contentBefore: "<ol><li>ab]cd</li><li>ef[gh</li></ol>",
                stepFunction: deleteBackward,
                contentAfter: "<ol><li>ab[]gh</li></ol>",
            });
        });

        test("should delete across an unindented list item and an indented list item", async () => {
            // Forward selection
            await testEditor({
                contentBefore: "<ol><li><p>ab[cd</p><ol><li>ef]gh</li></ol></li></ol>",
                stepFunction: deleteBackward,
                contentAfter: "<ol><li><p>ab[]gh</p></li></ol>",
            });
            // Backward selection
            await testEditor({
                contentBefore: "<ol><li><p>ab]cd</p><ol><li>ef[gh</li></ol></li></ol>",
                stepFunction: deleteBackward,
                contentAfter: "<ol><li><p>ab[]gh</p></li></ol>",
            });
        });

        test("should delete a list", async () => {
            // Forward selection
            await testEditor({
                contentBefore: "<p>abc[</p><ol><li><p>def]</p></li></ol>",
                stepFunction: deleteBackward,
                contentAfter: "<p>abc[]</p>",
            });
            // Backward selection
            await testEditor({
                contentBefore: "<p>abc]</p><ol><li><p>def[</p></li></ol>",
                stepFunction: deleteBackward,
                contentAfter: "<p>abc[]</p>",
            });
        });

        test("should merge the contents of a list item within a block into a heading, and leave the rest of its list as it is", async () => {
            // Forward selection
            await testEditor({
                contentBefore:
                    '<h1>a[b</h1><p>de</p><custom-block style="display: block;"><ol><li>fg</li><li>h]i</li><li>jk</li></ol></custom-block>',
                stepFunction: deleteBackward,
                contentAfter:
                    '<h1>a[]i</h1><custom-block style="display: block;"><ol><li>jk</li></ol></custom-block>',
            });
            // Backward selection
            await testEditor({
                contentBefore:
                    '<h1>a]b</h1><p>de</p><custom-block style="display: block;"><ol><li>fg</li><li>h[i</li><li>jk</li></ol></custom-block>',
                stepFunction: deleteBackward,
                contentAfter:
                    '<h1>a[]i</h1><custom-block style="display: block;"><ol><li>jk</li></ol></custom-block>',
            });
        });

        test("should not join the next list with the first one on delete range", async () => {
            await testEditor({
                contentBefore: "<ol><li>ab</li><li>[cd</li><li>ef]</li><li>gh</li></ol>",
                stepFunction: deleteBackward,
                contentAfter: "<ol><li>ab</li><li>[]<br></li><li>gh</li></ol>",
            });
        });
    });
    describe("Unordered", () => {
        test("should delete text within a list item", async () => {
            // Forward selection
            await testEditor({
                contentBefore: "<ul><li>ab[cd]ef</li></ul>",
                stepFunction: deleteBackward,
                contentAfter: "<ul><li>ab[]ef</li></ul>",
            });
            // Backward selection
            await testEditor({
                contentBefore: "<ul><li>ab]cd[ef</li></ul>",
                stepFunction: deleteBackward,
                contentAfter: "<ul><li>ab[]ef</li></ul>",
            });
        });

        test("should delete all the text in a list item", async () => {
            // Forward selection
            await testEditor({
                contentBefore: "<ul><li>[abc]</li></ul>",
                stepFunction: deleteBackward,
                contentAfter: "<ul><li>[]<br></li></ul>",
            });
            // Backward selection
            await testEditor({
                contentBefore: "<ul><li>]abc[</li></ul>",
                stepFunction: deleteBackward,
                contentAfter: "<ul><li>[]<br></li></ul>",
            });
        });

        test("should delete across two list items", async () => {
            // Forward selection
            await testEditor({
                contentBefore: "<ul><li>ab[cd</li><li>ef]gh</li></ul>",
                stepFunction: deleteBackward,
                contentAfter: "<ul><li>ab[]gh</li></ul>",
            });
            // Backward selection
            await testEditor({
                contentBefore: "<ul><li>ab]cd</li><li>ef[gh</li></ul>",
                stepFunction: deleteBackward,
                contentAfter: "<ul><li>ab[]gh</li></ul>",
            });
        });

        test("should delete across an unindented list item and an indented list item", async () => {
            // Forward selection
            await testEditor({
                contentBefore: "<ul><li><p>ab[cd</p><ul><li>ef]gh</li></ul></li></ul>",
                stepFunction: deleteBackward,
                contentAfter: "<ul><li><p>ab[]gh</p></li></ul>",
            });
            // Backward selection
            await testEditor({
                contentBefore: "<ul><li><p>ab]cd</p><ul><li>ef[gh</li></ul></li></ul>",
                stepFunction: deleteBackward,
                contentAfter: "<ul><li><p>ab[]gh</p></li></ul>",
            });
        });

        test("should delete a list", async () => {
            // Forward selection
            await testEditor({
                contentBefore: "<p>abc[</p><ul><li><p>def]</p></li></ul>",
                stepFunction: deleteBackward,
                contentAfter: "<p>abc[]</p>",
            });
            // Backward selection
            await testEditor({
                contentBefore: "<p>abc]</p><ul><li><p>def[</p></li></ul>",
                stepFunction: deleteBackward,
                contentAfter: "<p>abc[]</p>",
            });
        });

        test("should merge the contents of a list item within a block into a heading, and leave the rest of its list as it is", async () => {
            // Forward selection
            await testEditor({
                contentBefore:
                    '<h1>a[b</h1><p>de</p><custom-block style="display: block;"><ul><li>fg</li><li>h]i</li><li>jk</li></ul></custom-block>',
                stepFunction: deleteBackward,
                contentAfter:
                    '<h1>a[]i</h1><custom-block style="display: block;"><ul><li>jk</li></ul></custom-block>',
            });
            // Backward selection
            await testEditor({
                contentBefore:
                    '<h1>a]b</h1><p>de</p><custom-block style="display: block;"><ul><li>fg</li><li>h[i</li><li>jk</li></ul></custom-block>',
                stepFunction: deleteBackward,
                contentAfter:
                    '<h1>a[]i</h1><custom-block style="display: block;"><ul><li>jk</li></ul></custom-block>',
            });
        });
        test("should not join the next list with the first one on delete range", async () => {
            await testEditor({
                contentBefore: "<ul><li>ab</li><li>[cd</li><li>ef]</li><li>gh</li></ul>",
                stepFunction: deleteBackward,
                contentAfter: "<ul><li>ab</li><li>[]<br></li><li>gh</li></ul>",
            });
        });
    });
    describe("Checklist", () => {
        test("should delete text within a checklist item", async () => {
            // Forward selection
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li class="o_checked">ab[cd]ef</li></ul>',
                stepFunction: deleteBackward,
                contentAfter: '<ul class="o_checklist"><li class="o_checked">ab[]ef</li></ul>',
            });
            // Backward selection
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li class="o_checked">ab]cd[ef</li></ul>',
                stepFunction: deleteBackward,
                contentAfter: '<ul class="o_checklist"><li class="o_checked">ab[]ef</li></ul>',
            });
        });

        test("should delete all the text in a checklist item", async () => {
            // Forward selection
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li class="o_checked">[abc]</li></ul>',
                stepFunction: deleteBackward,
                contentAfter: '<ul class="o_checklist"><li class="o_checked">[]<br></li></ul>',
            });
            // Backward selection
            await testEditor({
                contentBefore: '<ul class="o_checklist"><li class="o_checked">]abc[</li></ul>',
                stepFunction: deleteBackward,
                contentAfter: '<ul class="o_checklist"><li class="o_checked">[]<br></li></ul>',
            });
        });

        describe("should delete across two list items", () => {
            // Forward selection
            test("should delete across two list items (1)", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li class="o_checked">ab[cd</li><li class="o_checked">ef]gh</li></ul>',
                    stepFunction: deleteBackward,
                    contentAfter: '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                });
            });
            test("should delete across two list items (2)", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li class="o_checked">ab[cd</li><li>ef]gh</li></ul>',
                    stepFunction: deleteBackward,
                    contentAfter: '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                });
            });
            // Backward selection
            test("should delete across two list items (3)", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li class="o_checked">ab]cd</li><li class="o_checked">ef[gh</li></ul>',
                    stepFunction: deleteBackward,
                    contentAfter: '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                });
            });
            test("should delete across two list items (4)", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li class="o_checked">ab]cd</li><li>ef[gh</li></ul>',
                    stepFunction: deleteBackward,
                    contentAfter: '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                });
            });
        });

        describe("should delete across an unindented list item and an indented list item", () => {
            // Forward selection
            test("should delete across an unindented list item and an indented list item (1)", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li><p>ab[cd</p><ul class="o_checklist"><li class="o_checked">ef]gh</li></ul></li></ul>',
                    stepFunction: deleteBackward,
                    contentAfter: '<ul class="o_checklist"><li><p>ab[]gh</p></li></ul>',
                });
            });
            test("should delete across an unindented list item and an indented list item (2)", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li><p>ab[cd</p><ul class="o_checklist"><li>ef]gh</li></ul></li></ul>',
                    stepFunction: deleteBackward,
                    // The indented list cannot be unchecked while its
                    // parent is checked: it gets checked automatically
                    // as a result. So "efgh" gets rendered as checked.
                    // Given that the parent list item was explicitely
                    // set as "checked", that status is preserved.
                    contentAfter: '<ul class="o_checklist"><li><p>ab[]gh</p></li></ul>',
                });
            });
            // Backward selection
            test("should delete across an unindented list item and an indented list item (3)", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li><p>ab]cd</p><ul class="o_checklist"><li class="o_checked">ef[gh</li></ul></li></ul>',
                    stepFunction: deleteBackward,
                    contentAfter: '<ul class="o_checklist"><li><p>ab[]gh</p></li></ul>',
                });
            });
            test("should delete across an unindented list item and an indented list item (4)", async () => {
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li><p>ab]cd</p><ul class="o_checklist"><li>ef[gh</li></ul></li></ul>',
                    stepFunction: deleteBackward,
                    // The indented list cannot be unchecked while its
                    // parent is checked: it gets checked automatically
                    // as a result. So "efgh" gets rendered as checked.
                    // Given that the parent list item was explicitely
                    // set as "checked", that status is preserved.
                    contentAfter: '<ul class="o_checklist"><li><p>ab[]gh</p></li></ul>',
                });
            });
        });

        test("should delete a checklist", async () => {
            // Forward selection
            await testEditor({
                contentBefore:
                    '<p>abc[</p><ul class="o_checklist"><li class="o_checked"><p>def]</p></li></ul>',
                stepFunction: deleteBackward,
                contentAfter: "<p>abc[]</p>",
            });
            // Backward selection
            await testEditor({
                contentBefore:
                    '<p>abc]</p><ul class="o_checklist"><li class="o_checked"><p>def[</p></li></ul>',
                stepFunction: deleteBackward,
                contentAfter: "<p>abc[]</p>",
            });
        });

        test("should merge the contents of a checklist item within a block into a heading, and leave the rest of its list as it is", async () => {
            // Forward selection
            await testEditor({
                contentBefore:
                    '<h1>a[b</h1><p>de</p><custom-block style="display:block;"><ul class="o_checklist"><li class="o_checked">fg</li><li class="o_checked">h]i</li><li class="o_checked">jk</li></ul></custom-block>',
                stepFunction: deleteBackward,
                contentAfter:
                    '<h1>a[]i</h1><custom-block style="display:block;"><ul class="o_checklist"><li class="o_checked">jk</li></ul></custom-block>',
            });
            // Backward selection
            await testEditor({
                contentBefore:
                    '<h1>a]b</h1><p>de</p><custom-block style="display:block;"><ul class="o_checklist"><li class="o_checked">fg</li><li class="o_checked">h[i</li><li class="o_checked">jk</li></ul></custom-block>',
                stepFunction: deleteBackward,
                contentAfter:
                    '<h1>a[]i</h1><custom-block style="display:block;"><ul class="o_checklist"><li class="o_checked">jk</li></ul></custom-block>',
            });
        });

        test("should not join the next list with the first one on delete range", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li>ab</li><li class="o_checked">[cd</li><li>ef]</li><li>gh</li></ul>',
                stepFunction: deleteBackward,
                contentAfter: '<ul class="o_checklist"><li>ab</li><li>[]<br></li><li>gh</li></ul>',
            });
        });

        test("should remove the o_checked class on delete range", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li>ab</li><li class="o_checked"><a href="#">[cd</a></li><li>ef]</li><li>gh</li></ul>',
                stepFunction: deleteBackward,
                contentAfterEdit:
                    '<ul class="o_checklist"><li>ab</li><li o-we-hint-text="List" class="o-we-hint">[]<br></li><li>gh</li></ul>',
                contentAfter: '<ul class="o_checklist"><li>ab</li><li>[]<br></li><li>gh</li></ul>',
            });
        });

        test("should remove the o_checked class on delete range (2)", async () => {
            await testEditor({
                contentBefore:
                    '<ul class="o_checklist"><li>ab</li><li class="o_checked"><h1>[cd</h1></li><li>ef]</li><li>gh</li></ul>',
                stepFunction: deleteBackward,
                contentAfter:
                    '<ul class="o_checklist"><li>ab</li><li><h1>[]<br></h1></li><li>gh</li></ul>',
            });
        });
    });
    describe("Mixed", () => {
        describe("Ordered to unordered", () => {
            test("should delete across an ordered list and an unordered list", async () => {
                // Forward selection
                await testEditor({
                    contentBefore: "<ol><li>ab[cd</li></ol><ul><li>ef]gh</li></ul>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ol><li>ab[]gh</li></ol>",
                });
                // Backward selection
                await testEditor({
                    contentBefore: "<ol><li>ab]cd</li></ol><ul><li>ef[gh</li></ul>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ol><li>ab[]gh</li></ol>",
                });
                // Forward selection
                await testEditor({
                    contentBefore:
                        "<ol><li>ab</li><li>[cd</li></ol><ul><li>ef]</li><li>gh</li></ul>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ol><li>ab</li></ol><ul><li>[]<br></li><li>gh</li></ul>",
                });
                // Backward selection
                await testEditor({
                    contentBefore:
                        "<ol><li>ab</li><li>]cd</li></ol><ul><li>ef[</li><li>gh</li></ul>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ol><li>ab</li></ol><ul><li>[]<br></li><li>gh</li></ul>",
                });
                // Forward selection
                await testEditor({
                    contentBefore:
                        "<ol><li>ab</li><li>[cd</li></ol><ul><li>e]f</li><li>gh</li></ul>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ol><li>ab</li></ol><ul><li>[]f</li><li>gh</li></ul>",
                });
                // Backward selection
                await testEditor({
                    contentBefore:
                        "<ol><li>ab</li><li>]cd</li></ol><ul><li>e[f</li><li>gh</li></ul>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ol><li>ab</li></ol><ul><li>[]f</li><li>gh</li></ul>",
                });
            });

            test("should delete across an ordered list item and an unordered list item within an ordered list", async () => {
                // Forward selection
                await testEditor({
                    contentBefore: "<ol><li><p>ab[cd</p><ul><li>ef]gh</li></ul></li></ol>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ol><li><p>ab[]gh</p></li></ol>",
                });
                await testEditor({
                    contentBefore: "<ol><li><p>[abcd</p><ul><li>efgh]</li></ul></li></ol>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ol><li><p>[]<br></p></li></ol>",
                });
                // Backward selection
                await testEditor({
                    contentBefore: "<ol><li><p>ab]cd</p><ul><li>ef[gh</li></ul></li></ol>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ol><li><p>ab[]gh</p></li></ol>",
                });
                await testEditor({
                    contentBefore: "<ol><li><p>]abcd</p><ul><li>efgh[</li></ul></li></ol>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ol><li><p>[]<br></p></li></ol>",
                });
            });

            test("should delete an ordered list and an unordered list", async () => {
                // Forward selection
                await testEditor({
                    contentBefore: "<p>ab[</p><ul><li>cd</li></ul><ol><li>ef]</li></ol>",
                    stepFunction: deleteBackward,
                    contentAfter: "<p>ab[]</p>",
                });
                // Backward selection
                await testEditor({
                    contentBefore: "<p>ab]</p><ul><li>cd</li></ul><ol><li>ef[</li></ol>",
                    stepFunction: deleteBackward,
                    contentAfter: "<p>ab[]</p>",
                });
            });
        });
        describe("Unordered to ordered", () => {
            test("should delete across an unordered list and an ordered list", async () => {
                // Forward selection
                await testEditor({
                    contentBefore: "<ul><li>ab[cd</li></ul><ol><li>ef]gh</li></ol>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ul><li>ab[]gh</li></ul>",
                });
                // Backward selection
                await testEditor({
                    contentBefore: "<ul><li>ab]cd</li></ul><ol><li>ef[gh</li></ol>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ul><li>ab[]gh</li></ul>",
                });
                // Forward selection
                await testEditor({
                    contentBefore:
                        "<ul><li>ab</li><li>[cd</li></ul><ol><li>ef]</li><li>gh</li></ol>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ul><li>ab</li></ul><ol><li>[]<br></li><li>gh</li></ol>",
                });
                // Backward selection
                await testEditor({
                    contentBefore:
                        "<ul><li>ab</li><li>]cd</li></ul><ol><li>ef[</li><li>gh</li></ol>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ul><li>ab</li></ul><ol><li>[]<br></li><li>gh</li></ol>",
                });
                // Forward selection
                await testEditor({
                    contentBefore:
                        "<ul><li>ab</li><li>[cd</li></ul><ol><li>e]f</li><li>gh</li></ol>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ul><li>ab</li></ul><ol><li>[]f</li><li>gh</li></ol>",
                });
                // Backward selection
                await testEditor({
                    contentBefore:
                        "<ul><li>ab</li><li>]cd</li></ul><ol><li>e[f</li><li>gh</li></ol>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ul><li>ab</li></ul><ol><li>[]f</li><li>gh</li></ol>",
                });
            });

            test("should delete across an unordered list item and an ordered list item within an unordered list", async () => {
                // Forward selection
                await testEditor({
                    contentBefore: "<ul><li><p>ab[cd</p><ol><li>ef]gh</li></ol></li></ul>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ul><li><p>ab[]gh</p></li></ul>",
                });
                // Backward selection
                await testEditor({
                    contentBefore: "<ul><li><p>ab]cd</p><ol><li>ef[gh</li></ol></li></ul>",
                    stepFunction: deleteBackward,
                    contentAfter: "<ul><li><p>ab[]gh</p></li></ul>",
                });
            });

            test("should delete an ordered list and an unordered list", async () => {
                // Forward selection
                await testEditor({
                    contentBefore: "<p>ab[</p><ol><li>cd</li></ol><ul><li>ef]</li></ul>",
                    stepFunction: deleteBackward,
                    contentAfter: "<p>ab[]</p>",
                });
                // Backward selection
                await testEditor({
                    contentBefore: "<p>ab]</p><ol><li>cd</li></ol><ul><li>ef[</li></ul>",
                    stepFunction: deleteBackward,
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
                            '<ul class="o_checklist"><li class="o_checked">ab[cd</li></ul><ul><li>ef]gh</li></ul>',
                        stepFunction: deleteBackward,
                        contentAfter:
                            '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                    });
                });
                test("should delete across an checklist list and an unordered list (2)", async () => {
                    // Backward selection
                    await testEditor({
                        contentBefore:
                            '<ul class="o_checklist"><li class="o_checked">ab]cd</li></ul><ul><li>ef[gh</li></ul>',
                        stepFunction: deleteBackward,
                        contentAfter:
                            '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                    });
                });
                test("should delete across an checklist list and an unordered list (3)", async () => {
                    // Forward selection
                    await testEditor({
                        contentBefore:
                            '<ul class="o_checklist"><li>ab</li><li>[cd</li></ul><ul><li>ef]</li><li>gh</li></ul>',
                        stepFunction: deleteBackward,
                        contentAfter:
                            '<ul class="o_checklist"><li>ab</li></ul><ul><li>[]<br></li><li>gh</li></ul>',
                    });
                });
                test("should delete across an checklist list and an unordered list (4)", async () => {
                    // Backward selection
                    await testEditor({
                        contentBefore:
                            '<ul class="o_checklist"><li>ab</li><li>]cd</li></ul><ul><li>ef[</li><li>gh</li></ul>',
                        stepFunction: deleteBackward,
                        contentAfter:
                            '<ul class="o_checklist"><li>ab</li></ul><ul><li>[]<br></li><li>gh</li></ul>',
                    });
                });
                test("should delete across an checklist list and an unordered list (5)", async () => {
                    // Forward selection
                    await testEditor({
                        contentBefore:
                            '<ul class="o_checklist"><li>ab</li><li>[cd</li></ul><ul><li>e]f</li><li>gh</li></ul>',
                        stepFunction: deleteBackward,
                        contentAfter:
                            '<ul class="o_checklist"><li>ab</li></ul><ul><li>[]f</li><li>gh</li></ul>',
                    });
                });
                test("should delete across an checklist list and an unordered list (6)", async () => {
                    // Backward selection
                    await testEditor({
                        contentBefore:
                            '<ul class="o_checklist"><li>ab</li><li>]cd</li></ul><ul><li>e[f</li><li>gh</li></ul>',
                        stepFunction: deleteBackward,
                        contentAfter:
                            '<ul class="o_checklist"><li>ab</li></ul><ul><li>[]f</li><li>gh</li></ul>',
                    });
                });
            });

            test("should delete across an checklist list item and an unordered list item within an checklist list", async () => {
                // Forward selection
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li><p>ab[cd</p><ul><li>ef]gh</li></ul></li></ul>',
                    stepFunction: deleteBackward,
                    contentAfter: '<ul class="o_checklist"><li><p>ab[]gh</p></li></ul>',
                });
                // Backward selection
                await testEditor({
                    contentBefore:
                        '<ul class="o_checklist"><li><p>ab]cd</p><ul><li>ef[gh</li></ul></li></ul>',
                    stepFunction: deleteBackward,
                    contentAfter: '<ul class="o_checklist"><li><p>ab[]gh</p></li></ul>',
                });
            });

            test("should delete an checklist list and an unordered list", async () => {
                // Forward selection
                await testEditor({
                    contentBefore:
                        '<p>ab[</p><ul><li>cd</li></ul><ul class="o_checklist"><li class="o_checked">ef]</li></ul>',
                    stepFunction: deleteBackward,
                    contentAfter: "<p>ab[]</p>",
                });
                // Backward selection
                await testEditor({
                    contentBefore:
                        '<p>ab]</p><ul><li>cd</li></ul><ul class="o_checklist"><li class="o_checked">ef[</li></ul>',
                    stepFunction: deleteBackward,
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
                    stepFunction: deleteBackward,
                    contentAfter: "<ul><li>ab[]gh</li></ul>",
                });
                // Backward selection
                await testEditor({
                    contentBefore:
                        '<ul><li>ab]cd</li></ul><ul class="o_checklist"><li class="o_checked">ef[gh</li></ul>',
                    stepFunction: deleteBackward,
                    contentAfter: "<ul><li>ab[]gh</li></ul>",
                });
                // Forward selection
                await testEditor({
                    contentBefore:
                        '<ul><li>ab</li><li>[cd</li></ul><ul class="o_checklist"><li>ef]</li><li>gh</li></ul>',
                    stepFunction: deleteBackward,
                    contentAfter:
                        '<ul><li>ab</li></ul><ul class="o_checklist"><li>[]<br></li><li>gh</li></ul>',
                });
                // Backward selection
                await testEditor({
                    contentBefore:
                        '<ul><li>ab</li><li>]cd</li></ul><ul class="o_checklist"><li>ef[</li><li>gh</li></ul>',
                    stepFunction: deleteBackward,
                    contentAfter:
                        '<ul><li>ab</li></ul><ul class="o_checklist"><li>[]<br></li><li>gh</li></ul>',
                });
                // Forward selection
                await testEditor({
                    contentBefore:
                        '<ul><li>ab</li><li>[cd</li></ul><ul class="o_checklist"><li>e]f</li><li>gh</li></ul>',
                    stepFunction: deleteBackward,
                    contentAfter:
                        '<ul><li>ab</li></ul><ul class="o_checklist"><li>[]f</li><li>gh</li></ul>',
                });
                // Backward selection
                await testEditor({
                    contentBefore:
                        '<ul><li>ab</li><li>]cd</li></ul><ul class="o_checklist"><li>e[f</li><li>gh</li></ul>',
                    stepFunction: deleteBackward,
                    contentAfter:
                        '<ul><li>ab</li></ul><ul class="o_checklist"><li>[]f</li><li>gh</li></ul>',
                });
            });

            test("should delete across an unordered list item and an checklist list item within an unordered list", async () => {
                // Forward selection
                await testEditor({
                    contentBefore:
                        '<ul><li><p>ab[cd</p><ul class="o_checklist"><li class="o_checked">ef]gh</li></ul></li></ul>',
                    stepFunction: deleteBackward,
                    contentAfter: "<ul><li><p>ab[]gh</p></li></ul>",
                });
                // Backward selection
                await testEditor({
                    contentBefore:
                        '<ul><li><p>ab]cd</p><ul class="o_checklist"><li class="o_checked">ef[gh</li></ul></li></ul>',
                    stepFunction: deleteBackward,
                    contentAfter: "<ul><li><p>ab[]gh</p></li></ul>",
                });
            });

            test("should delete an checklist list and an unordered list", async () => {
                // Forward selection
                await testEditor({
                    contentBefore:
                        '<p>ab[</p><ul class="o_checklist"><li class="o_checked">cd</li></ul><ul><li>ef]</li></ul>',
                    stepFunction: deleteBackward,
                    contentAfter: "<p>ab[]</p>",
                });
                // Backward selection
                await testEditor({
                    contentBefore:
                        '<p>ab]</p><ul class="o_checklist"><li class="o_checked">cd</li></ul><ul><li>ef[</li></ul>',
                    stepFunction: deleteBackward,
                    contentAfter: "<p>ab[]</p>",
                });
            });
        });
    });
});

test("shoud merge list item in the previous breakable sibling", async () => {
    await testEditor({
        contentBefore: unformat(`
                <p>a[bc</p>
                <ol>
                    <li>d]ef</li>
                    <li>ghi</li>
                </ol>`),
        stepFunction: deleteBackward,
        contentAfter: unformat(`
                <p>a[]ef</p>
                <ol>
                    <li>ghi</li>
                </ol>`),
    });
    await testEditor({
        contentBefore: unformat(`
                <custom-block style="display: block;">
                    <p>a[bc</p>
                </custom-block>
                <ol>
                    <li>d]ef</li>
                    <li>ghi</li>
                </ol>`),
        stepFunction: deleteBackward,
        contentAfter: unformat(`
                <custom-block style="display: block;">
                    <p>a[]ef</p>
                </custom-block>
                <ol>
                    <li>ghi</li>
                </ol>`),
    });
});
