import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { manuallyDispatchProgrammaticEvent, microTick, press } from "@odoo/hoot-dom";
import { animationFrame, tick } from "@odoo/hoot-mock";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { setupEditor, testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { getContent, setSelection } from "../_helpers/selection";
import { deleteBackward, insertText, splitTripleClick, undo } from "../_helpers/user_actions";

/**
 * content of the "deleteBackward" sub suite in editor.test.js
 */

describe("Selection collapsed", () => {
    describe("Basic", () => {
        test("should do nothing", async () => {
            // TODO the addition of <br/> "correction" part was judged
            // unnecessary to enforce, the rest of the test still makes
            // sense: not removing the unique <p/> and keeping the
            // cursor at the right place.
            await testEditor({
                contentBefore: "<p>[]</p>",
                stepFunction: deleteBackward,
                contentAfter: "<p>[]</p>",
            });
            // TODO this cannot actually be tested currently as a
            // backspace/delete in that case is not even detected
            // (no input event to rollback)
            // await testEditor({
            //     contentBefore: '<p>[<br>]</p>',
            //     stepFunction: deleteBackward,
            //     // The <br> is there only to make the <p> visible.
            //     // It does not exist in VDocument and selecting it
            //     // has no meaning in the DOM.
            //     contentAfter: '<p>[]<br></p>',
            // });
            await testEditor({
                contentBefore: "<p>[]abc</p>",
                stepFunction: deleteBackward,
                contentAfter: "<p>[]abc</p>",
            });
        });

        test("should delete the first character in a paragraph", async () => {
            await testEditor({
                contentBefore: "<p>a[]bc</p>",
                stepFunction: deleteBackward,
                contentAfter: "<p>[]bc</p>",
            });
        });

        test("should delete a character within a paragraph", async () => {
            await testEditor({
                contentBefore: "<p>ab[]c</p>",
                stepFunction: deleteBackward,
                contentAfter: "<p>a[]c</p>",
            });
        });

        test("should delete the last character in a paragraph", async () => {
            await testEditor({
                contentBefore: "<p>abc[]</p>",
                stepFunction: deleteBackward,
                contentAfter: "<p>ab[]</p>",
            });
            await testEditor({
                contentBefore: "<p>ab c[]</p>",
                stepFunction: deleteBackward,
                // The space should be converted to an unbreakable space
                // so it is visible.
                contentAfter: "<p>ab&nbsp;[]</p>",
            });
        });

        test("should merge a paragraph into an empty paragraph", async () => {
            await testEditor({
                contentBefore: "<p><br></p><p>[]abc</p>",
                stepFunction: deleteBackward,
                contentAfter: "<p>[]abc</p>",
            });
        });

        test("should merge node correctly", async () => {
            await testEditor({
                contentBefore: '<div>a<span class="a">b</span><p>[]c</p>d</div>',
                stepFunction: deleteBackward,
                contentAfter: '<div>a<span class="a">b[]</span>c<br>d</div>',
            });
        });

        test("should ignore ZWS", async () => {
            await testEditor({
                contentBefore: "<p>ab\u200B[]c</p>",
                stepFunction: deleteBackward,
                contentAfter: "<p>a[]c</p>",
            });
        });

        test("should keep inline block", async () => {
            await testEditor({
                contentBefore: "<div><p>ab</p><br><i>c[]</i></div>",
                stepFunction: deleteBackward,
                contentAfterEdit:
                    '<div><p>ab</p><br><i data-oe-zws-empty-inline="">[]\u200B</i></div>',
                contentAfter: "<div><p>ab</p><br><br>[]</div>",
            });
            await testEditor({
                contentBefore: '<div><p>uv</p><br><span class="style">w[]</span></div>',
                stepFunction: deleteBackward,
                contentAfterEdit:
                    '<div><p>uv</p><br><span class="style" data-oe-zws-empty-inline="">[]\u200B</span></div>',
                contentAfter: '<div><p>uv</p><br><span class="style">[]\u200B</span></div>',
            });
            await testEditor({
                contentBefore: '<div><p>cd</p><br><span class="a">e[]</span></div>',
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                    await insertText(editor, "x");
                },
                contentAfterEdit: '<div><p>cd</p><br><span class="a">x[]</span></div>',
                contentAfter: '<div><p>cd</p><br><span class="a">x[]</span></div>',
            });
        });
        test("should keep inline block and then undo (1)", async () => {
            await testEditor({
                contentBefore: "<p>ab<b>c[]</b>de</p>",
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                    await insertText(editor, "x");
                    undo(editor);
                },
                contentAfterEdit: '<p>ab<b data-oe-zws-empty-inline="">[]\u200B</b>de</p>',
                contentAfter: "<p>ab[]de</p>",
            });
        });
        test("should keep inline block and then undo (2)", async () => {
            await testEditor({
                contentBefore: "<p>ab<b>c[]</b>de</p>",
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                    await insertText(editor, "x");
                    undo(editor);
                    undo(editor);
                },
                contentAfterEdit: "<p>ab<b>c[]</b>de</p>",
                contentAfter: "<p>ab<b>c[]</b>de</p>",
            });
        });

        test("should delete through ZWS and Empty Inline", async () => {
            await testEditor({
                contentBefore: '<p>ab<span class="style">c</span>d[]e</p>',
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                    deleteBackward(editor);
                    deleteBackward(editor);
                },
                contentAfter: "<p>a[]e</p>",
            });
        });

        test("ZWS: should delete element content but keep cursor in", async () => {
            await testEditor({
                contentBefore: '<p>uv<i style="color:red">w[]</i>xy</p>',
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                },
                contentAfterEdit:
                    '<p>uv<i style="color:red" data-oe-zws-empty-inline="">[]\u200B</i>xy</p>',
                contentAfter: "<p>uv[]xy</p>",
            });
            await testEditor({
                contentBefore: '<p>uv<i style="color:red">w[]</i>xy</p>',
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                    await insertText(editor, "i");
                },
                contentAfterEdit: '<p>uv<i style="color:red">i[]</i>xy</p>',
                contentAfter: '<p>uv<i style="color:red">i[]</i>xy</p>',
            });
            await testEditor({
                contentBefore: '<p>ab<span class="style">cd[]</span>ef</p>',
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                    deleteBackward(editor);
                },
                contentAfterEdit:
                    '<p>ab<span class="style" data-oe-zws-empty-inline="">[]\u200B</span>ef</p>',
                contentAfter: '<p>ab<span class="style">[]\u200B</span>ef</p>',
            });
            await testEditor({
                contentBefore: '<p>ab<span class="style">cd[]</span>ef</p>',
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                    deleteBackward(editor);
                    await insertText(editor, "x");
                },
                contentAfterEdit: '<p>ab<span class="style">x[]</span>ef</p>',
                contentAfter: '<p>ab<span class="style">x[]</span>ef</p>',
            });
        });

        test("should ignore ZWS and merge (1)", async () => {
            await testEditor({
                contentBefore:
                    '<p><b>ab</b><span class="removeme" data-oe-zws-empty-inline="">[]\u200B</span></p>',
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                    await insertText(editor, "x");
                },
                contentAfter: "<p><b>ax[]</b></p>",
            });
            await testEditor({
                contentBefore:
                    '<p><span class="a">cd</span><span class="removeme" data-oe-zws-empty-inline="">[]\u200B</span></p>',
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                    await insertText(editor, "x");
                },
                contentAfter: '<p><span class="a">cx[]</span></p>',
            });
            await testEditor({
                contentBefore:
                    '<p><b>ef</b><br><span class="removeme" data-oe-zws-empty-inline="">[]\u200B</span></p>',
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                    await insertText(editor, "x");
                },
                contentAfter: "<p><b>efx[]</b></p>",
            });
        });

        test("should ignore ZWS and merge (2)", async () => {
            await testEditor({
                contentBefore: '<div><p>ab</p><span class="a">[]\u200B</span></div>',
                stepFunction: deleteBackward,
                contentAfter: "<div><p>ab[]</p></div>",
            });
            await testEditor({
                contentBefore: '<div><p>cd</p><br><span class="a">[]\u200B</span></div>',
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                    await insertText(editor, "x");
                },
                contentAfter: "<div><p>cd</p>x[]</div>",
            });
        });

        test("should not remove empty Bootstrap column", async () => {
            await testEditor({
                contentBefore: '<div><div><p>ABC</p></div><div class="col">X[]</div></div>',
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                    deleteBackward(editor);
                    deleteBackward(editor);
                },
                contentAfter: '<div><div><p>ABC</p></div><div class="col">[]<br></div></div>',
            });
            await testEditor({
                contentBefore: '<div><div><p>ABC</p></div><div class="col-12">X[]</div></div>',
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                    deleteBackward(editor);
                    deleteBackward(editor);
                },
                contentAfter: '<div><div><p>ABC</p></div><div class="col-12">[]<br></div></div>',
            });
            await testEditor({
                contentBefore: '<div><div><p>ABC</p></div><div class="col-lg-3">X[]</div></div>',
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                    deleteBackward(editor);
                    deleteBackward(editor);
                },
                contentAfter: '<div><div><p>ABC</p></div><div class="col-lg-3">[]<br></div></div>',
            });
        });

        test("should merge the following inline text node", async () => {
            await testEditor({
                contentBefore: "<div><p>abc</p>[]def</div>",
                stepFunction: deleteBackward,
                contentAfter: "<div><p>abc[]def</p></div>",
            });
            await testEditor({
                contentBefore: "<div><p>abc</p>[]def<p>ghi</p></div>",
                stepFunction: deleteBackward,
                contentAfter: "<div><p>abc[]def</p><p>ghi</p></div>",
            });
        });

        test("should merge paragraphs", async () => {
            await testEditor({
                contentBefore: '<p>abc</p><p style="margin-bottom: 0px;">[]def</p>',
                stepFunction: deleteBackward,
                contentAfter: "<p>abc[]def</p>",
            });
            await testEditor({
                contentBefore: '<p>abc</p><p style="margin-bottom: 0px;">[]def</p><p>ghi</p>',
                stepFunction: deleteBackward,
                contentAfter: "<p>abc[]def</p><p>ghi</p>",
            });
        });

        test("should delete starting white space and merge paragraphs", async () => {
            await testEditor({
                contentBefore: `<p>mollis.</p><p>\n <i>[]Pe</i><i>lentesque</i></p>`,
                stepFunction: deleteBackward,
                contentAfter: `<p>mollis.[]<i>Pelentesque</i></p>`,
            });
        });

        test('should remove contenteditable="false"', async () => {
            await testEditor({
                contentBefore: `<p><span contenteditable="false">abc</span>[]def</p>`,
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                },
                contentAfter: `<p>[]def</p>`,
            });
        });

        test('should remove contenteditable="false" at the beggining of a P', async () => {
            await testEditor({
                contentBefore: `<p>abc</p><div contenteditable="false">def</div><p>[]ghi</p>`,
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                },
                contentAfter: `<p>abc</p><p>[]ghi</p>`,
            });
        });

        test("should remove a fontawesome", async () => {
            await testEditor({
                contentBefore: `<div><p>abc<span class="fa"></span>[]def</p></div>`,
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                },
                contentAfter: `<div><p>abc[]def</p></div>`,
            });
        });

        test("should unwrap a block next to an inline sibling element", async () => {
            await testEditor({
                contentBefore: `<div><p>abc</p><span contenteditable="false">xyz</span><p>[]def</p></div>`,
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                },
                contentAfter: `<div><p>abc</p><span contenteditable="false">xyz</span>[]def</div>`,
            });
        });

        test("should unwrap a block next to an inline unbreakable element", async () => {
            await testEditor({
                contentBefore: `<div><p>abc</p><div class="o_image"></div><p>[]def</p></div>`,
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                },
                contentAfter: `<div><p>abc</p><div class="o_image"></div>[]def</div>`,
            });
        });

        test("should remove an inline unbreakable contenteditable='false' sibling element", async () => {
            await testEditor({
                contentBefore: `<div><p>abc</p><div class="o_image"></div>[]def</div>`,
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                },
                contentAfter: `<div><p>abc</p>[]def</div>`,
            });
        });

        test("should not remove an inline contenteditable='false' in a previous sibling", async () => {
            await testEditor({
                contentBefore: `<p>a<span contenteditable="false">bc</span></p><p>[]<br></p>`,
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                },
                contentAfter: `<p>a<span contenteditable="false">bc</span>[]</p>`,
            });
        });

        test("should not remove a non editable sibling (inline)", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <div contenteditable="false">
                        <span class="a">a</span>
                        <div contenteditable="true">
                            <p>[]<br></p>
                        </div>
                    </div>
                `),
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                },
                contentAfter: unformat(`
                    <div contenteditable="false">
                        <span class="a">a</span>
                        <div contenteditable="true">
                            <p>[]<br></p>
                        </div>
                    </div>
                `),
            });
        });

        test("should not remove a non editable sibling (block)", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <div contenteditable="false">
                        <div class="a">a<span>a</span></div>
                        <div contenteditable="true">
                            <p>[]<br></p>
                        </div>
                    </div>
                `),
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                },
                contentAfter: unformat(`
                    <div contenteditable="false">
                        <div class="a">a<span>a</span></div>
                        <div contenteditable="true">
                            <p>[]<br></p>
                        </div>
                    </div>
                `),
            });
        });

        test("should remove a hr", async () => {
            await testEditor({
                contentBefore: `<div><p>abc</p><hr><p>[]def</p></div>`,
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                },
                contentAfter: `<div><p>abc</p><p>[]def</p></div>`,
            });
        });

        test("should merge paragraph with previous one containing a media element", async () => {
            await testEditor({
                contentBefore: `<p>abc</p><p style="margin-bottom: 0px;"><o-image class="o_image" contenteditable="false"></o-image></p><p>[]def</p>`,
                stepFunction: deleteBackward,
                contentAfterEdit: `<p>abc</p><p style="margin-bottom: 0px;"><o-image class="o_image" contenteditable="false"></o-image>[]def</p>`,
                contentAfter: `<p>abc</p><p style="margin-bottom: 0px;"><o-image class="o_image"></o-image>[]def</p>`,
            });
        });

        test("should remove a media element inside a p", async () => {
            await testEditor({
                contentBefore: `<p>abc</p><p style="margin-bottom: 0px;"><o-image class="o_image" contenteditable="false"></o-image>[]def</p>`,
                stepFunction: deleteBackward,
                contentAfter: `<p>abc</p><p style="margin-bottom: 0px;">[]def</p>`,
            });
        });

        test("should remove a link to uploaded document", async () => {
            await testEditor({
                contentBefore: `<p>abc<a href="#" title="document" data-mimetype="application/pdf" class="o_image" contenteditable="false"></a>[]</p>`,
                stepFunction: deleteBackward,
                contentAfter: `<p>abc[]</p>`,
            });
        });

        test("should remove a link to uploaded document at the beginning of the editable", async () => {
            await testEditor({
                contentBefore: `<p><a href="#" title="document" data-mimetype="application/pdf" class="o_image" contenteditable="false"></a>[]</p>`,
                stepFunction: deleteBackward,
                contentAfter: `<p>[]<br></p>`,
            });
        });

        test.todo("should not delete in contenteditable=false", async () => {
            await testEditor({
                contentBefore: `<p contenteditable="false">ab[]cdef</p>`,
                stepFunction: deleteBackward,
                contentAfter: `<p contenteditable="false">ab[]cdef</p>`,
            });
        });

        test("should merge p elements inside conteneditbale=true inside contenteditable=false", async () => {
            await testEditor({
                contentBefore: `<div contenteditable="false"><div contenteditable="true"><p>abc</p><p>[]def</p></div></div>`,
                stepFunction: deleteBackward,
                contentAfter: `<div contenteditable="false"><div contenteditable="true"><p>abc[]def</p></div></div>`,
            });
        });

        test("should not remove preceding character with U+0020 whitespace", async () => {
            await testEditor({
                contentBefore: `<p>abcd\u0020[]</p>`,
                stepFunction: deleteBackward,
                contentAfter: `<p>abcd[]</p>`,
            });
        });
        test("should delete only the button", async () => {
            await testEditor({
                contentBefore: `<p>a<a class="btn" href="#">[]</a></p>`,
                stepFunction: deleteBackward,
                contentAfter: `<p>a[]</p>`,
            });
        });
    });

    describe("Line breaks", () => {
        describe("Single", () => {
            test("should delete a leading line break", async () => {
                await testEditor({
                    contentBefore: "<p><br>[]abc</p>",
                    stepFunction: deleteBackward,
                    contentAfter: "<p>[]abc</p>",
                });
                await testEditor({
                    contentBefore: "<p><br>[] abc</p>",
                    stepFunction: deleteBackward,
                    // The space after the <br> is expected to be parsed
                    // away, like it is in the DOM.
                    contentAfter: "<p>[]abc</p>",
                });
            });

            test("should delete a line break within a paragraph", async () => {
                await testEditor({
                    contentBefore: "<p>ab<br>[]cd</p>",
                    stepFunction: deleteBackward,
                    contentAfter: "<p>ab[]cd</p>",
                });
                await testEditor({
                    contentBefore: "<p>ab <br>[]cd</p>",
                    stepFunction: deleteBackward,
                    contentAfter: "<p>ab []cd</p>",
                });
                await testEditor({
                    contentBefore: "<p>ab<br>[] cd</p>",
                    stepFunction: deleteBackward,
                    // The space after the <br> is expected to be parsed
                    // away, like it is in the DOM.
                    contentAfter: "<p>ab[]cd</p>",
                });
            });

            test("should delete a trailing line break", async () => {
                await testEditor({
                    contentBefore: "<p>abc<br><br>[]</p>",
                    stepFunction: deleteBackward,
                    contentAfter: "<p>abc[]</p>",
                });
                await testEditor({
                    contentBefore: "<p>abc<br>[]<br></p>",
                    stepFunction: deleteBackward,
                    contentAfter: "<p>abc[]</p>",
                });
                await testEditor({
                    contentBefore: "<p>abc <br><br>[]</p>",
                    stepFunction: deleteBackward,
                    contentAfter: "<p>abc&nbsp;[]</p>",
                });
            });

            test("should delete a character and a line break, emptying a paragraph", async () => {
                await testEditor({
                    contentBefore: "<p>aaa</p><p><br>a[]</p>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>aaa</p><p>[]<br></p>",
                });
            });

            test("should delete a character after a trailing line break", async () => {
                await testEditor({
                    contentBefore: "<p>ab<br>c[]</p>",
                    stepFunction: deleteBackward,
                    // A new <br> should be insterted, to make the first one
                    // visible.
                    contentAfter: "<p>ab<br>[]<br></p>",
                });
            });
        });

        describe("Consecutive", () => {
            test("should merge a paragraph with 4 <br> into a paragraph with text", async () => {
                // 1
                await testEditor({
                    contentBefore: "<p>ab</p><p>[]<br><br><br><br></p><p>cd</p>",
                    stepFunction: deleteBackward,
                    contentAfter: "<p>ab[]<br><br><br><br></p><p>cd</p>",
                });
            });

            test("should delete a line break (1)", async () => {
                // 2-1
                await testEditor({
                    contentBefore: "<p>ab</p><p><br>[]<br><br><br></p><p>cd</p>",
                    stepFunction: deleteBackward,
                    contentAfter: "<p>ab</p><p>[]<br><br><br></p><p>cd</p>",
                });
            });

            test("should delete a line break, then merge a paragraph with 3 <br> into a paragraph with text", async () => {
                // 2-2
                await testEditor({
                    contentBefore: "<p>ab</p><p><br>[]<br><br><br></p><p>cd</p>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>ab[]<br><br><br></p><p>cd</p>",
                });
            });

            test("should delete a line break (2)", async () => {
                // 3-1
                await testEditor({
                    contentBefore: "<p>ab</p><p><br><br>[]<br><br></p><p>cd</p>",
                    stepFunction: deleteBackward,
                    contentAfter: "<p>ab</p><p><br>[]<br><br></p><p>cd</p>",
                });
            });

            test("should delete two line breaks (3)", async () => {
                // 3-2
                await testEditor({
                    contentBefore: "<p>ab</p><p><br><br>[]<br><br></p><p>cd</p>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>ab</p><p>[]<br><br></p><p>cd</p>",
                });
            });

            test("should delete two line breaks, then merge a paragraph with 3 <br> into a paragraph with text", async () => {
                // 3-3
                await testEditor({
                    contentBefore: "<p>ab</p><p><br><br>[]<br><br></p><p>cd</p>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>ab[]<br><br></p><p>cd</p>",
                });
            });

            test("should delete a line break when several", async () => {
                // 4-1
                await testEditor({
                    contentBefore: "<p>ab</p><p><br><br><br>[]<br></p><p>cd</p>",
                    stepFunction: deleteBackward,
                    // A trailing line break is rendered as two <br>.
                    contentAfter: "<p>ab</p><p><br><br>[]<br></p><p>cd</p>",
                });
                // 5-1
                await testEditor({
                    contentBefore: "<p>ab</p><p><br><br><br><br>[]</p><p>cd</p>",
                    stepFunction: deleteBackward,
                    // This should be identical to 4-1
                    contentAfter: "<p>ab</p><p><br><br>[]<br></p><p>cd</p>",
                });
            });

            test("should delete two line breaks", async () => {
                // 4-2
                await testEditor({
                    contentBefore: "<p>ab</p><p><br><br><br>[]<br></p><p>cd</p>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    // A trailing line break is rendered as two <br>.
                    contentAfter: "<p>ab</p><p><br>[]<br></p><p>cd</p>",
                });
                // 5-2
                await testEditor({
                    contentBefore: "<p>ab</p><p><br><br><br><br>[]</p><p>cd</p>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    // This should be identical to 4-2
                    contentAfter: "<p>ab</p><p><br>[]<br></p><p>cd</p>",
                });
            });

            test("should delete three line breaks (emptying a paragraph)", async () => {
                // 4-3
                await testEditor({
                    contentBefore: "<p>ab</p><p><br><br><br>[]<br></p><p>cd</p>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>ab</p><p>[]<br></p><p>cd</p>",
                });
                // 5-3
                await testEditor({
                    contentBefore: "<p>ab</p><p><br><br><br><br>[]</p><p>cd</p>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    // This should be identical to 4-3
                    contentAfter: "<p>ab</p><p>[]<br></p><p>cd</p>",
                });
            });

            test("should delete three line breaks, then merge an empty parargaph into a paragraph with text", async () => {
                // 4-4
                await testEditor({
                    contentBefore: "<p>ab</p><p><br><br><br>[]<br></p><p>cd</p>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    // This should be identical to 4-4
                    contentAfter: "<p>ab[]</p><p>cd</p>",
                });
                // 5-4
                await testEditor({
                    contentBefore: "<p>ab</p><p><br><br><br><br>[]</p><p>cd</p>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>ab[]</p><p>cd</p>",
                });
            });

            test("should merge a paragraph into a paragraph with 4 <br>", async () => {
                // 6-1
                await testEditor({
                    contentBefore: "<p>ab</p><p><br><br><br><br></p><p>[]cd</p>",
                    stepFunction: deleteBackward,
                    contentAfter: "<p>ab</p><p><br><br><br>[]cd</p>",
                });
            });

            test("should merge a paragraph into a paragraph with 4 <br>, then delete a trailing line break", async () => {
                // 6-2
                await testEditor({
                    contentBefore: "<p>ab</p><p><br><br><br><br></p><p>[]cd</p>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>ab</p><p><br><br>[]cd</p>",
                });
            });

            test("should merge a paragraph into a paragraph with 4 <br>, then delete two line breaks", async () => {
                // 6-3
                await testEditor({
                    contentBefore: "<p>ab</p><p><br><br><br><br></p><p>[]cd</p>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>ab</p><p><br>[]cd</p>",
                });
            });

            test("should merge a paragraph into a paragraph with 4 <br>, then delete three line breaks", async () => {
                // 6-4
                await testEditor({
                    contentBefore: "<p>ab</p><p><br><br><br><br></p><p>[]cd</p>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>ab</p><p>[]cd</p>",
                });
            });

            test("should merge a paragraph into a paragraph with 4 <br>, then delete three line breaks, then merge two paragraphs with text", async () => {
                // 6-5
                await testEditor({
                    contentBefore: "<p>ab</p><p><br><br><br><br></p><p>[]cd</p>",
                    stepFunction: async (editor) => {
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                        deleteBackward(editor);
                    },
                    contentAfter: "<p>ab[]cd</p>",
                });
            });
        });
    });

    describe("Pre", () => {
        test("should delete a character in a pre", async () => {
            await testEditor({
                contentBefore: "<pre>ab[]cd</pre>",
                stepFunction: deleteBackward,
                contentAfter: "<pre>a[]cd</pre>",
            });
        });

        test("should delete a character in a pre (space before)", async () => {
            await testEditor({
                contentBefore: "<pre>     ab[]cd</pre>",
                stepFunction: deleteBackward,
                contentAfter: "<pre>     a[]cd</pre>",
            });
        });

        test("should delete a character in a pre (space after)", async () => {
            await testEditor({
                contentBefore: "<pre>ab[]cd     </pre>",
                stepFunction: deleteBackward,
                contentAfter: "<pre>a[]cd     </pre>",
            });
        });

        test("should delete a character in a pre (space before and after)", async () => {
            await testEditor({
                contentBefore: "<pre>     ab[]cd     </pre>",
                stepFunction: deleteBackward,
                contentAfter: "<pre>     a[]cd     </pre>",
            });
        });

        test("should delete a space in a pre", async () => {
            await testEditor({
                contentBefore: "<pre>   []  ab</pre>",
                stepFunction: deleteBackward,
                contentAfter: "<pre>  []  ab</pre>",
            });
        });

        test("should delete a newline in a pre", async () => {
            await testEditor({
                contentBefore: "<pre>ab\n[]cd</pre>",
                stepFunction: deleteBackward,
                contentAfter: "<pre>ab[]cd</pre>",
            });
        });

        test("should delete all leading space in a pre", async () => {
            await testEditor({
                contentBefore: "<pre>     []ab</pre>",
                stepFunction: async (BasicEditor) => {
                    deleteBackward(BasicEditor);
                    deleteBackward(BasicEditor);
                    deleteBackward(BasicEditor);
                    deleteBackward(BasicEditor);
                    deleteBackward(BasicEditor);
                },
                contentAfter: "<pre>[]ab</pre>",
            });
        });

        test("should delete all trailing space in a pre", async () => {
            await testEditor({
                contentBefore: "<pre>ab     []</pre>",
                stepFunction: async (BasicEditor) => {
                    deleteBackward(BasicEditor);
                    deleteBackward(BasicEditor);
                    deleteBackward(BasicEditor);
                    deleteBackward(BasicEditor);
                    deleteBackward(BasicEditor);
                },
                contentAfter: "<pre>ab[]</pre>",
            });
        });
    });

    describe("Formats", () => {
        test("should delete a character before a format node", async () => {
            await testEditor({
                contentBefore: "<p>abc<b>[]def</b></p>",
                stepFunction: deleteBackward,
                // The selection is normalized so we only have one way
                // to represent a position.
                contentAfter: "<p>ab[]<b>def</b></p>",
            });
            await testEditor({
                contentBefore: "<p>abc[]<b>def</b></p>",
                stepFunction: deleteBackward,
                contentAfter: "<p>ab[]<b>def</b></p>",
            });
        });
    });

    describe("Nested Elements", () => {
        test("should delete a h1 inside a td immediately after insertion", async () => {
            await testEditor({
                contentBefore:
                    "<table><tbody><tr><td>[]<br></td><td><br></td><td><br></td></tr><tr><td><br></td><td><br></td><td><br></td></tr><tr><td><br></td><td><br></td><td><br></td></tr></tbody></table>",
                stepFunction: async (editor) => {
                    await insertText(editor, "/");
                    await insertText(editor, "Heading");
                    await animationFrame();
                    await press("Enter");
                    deleteBackward(editor);
                },
                contentAfter:
                    "<table><tbody><tr><td><p>[]<br></p></td><td><br></td><td><br></td></tr><tr><td><br></td><td><br></td><td><br></td></tr><tr><td><br></td><td><br></td><td><br></td></tr></tbody></table>",
            });
        });

        test("should delete a h1 inside a nested list immediately after insertion", async () => {
            await testEditor({
                contentBefore:
                    '<ul><li>abc</li><li class="oe-nested"><ul><li>[]<br></li></ul></li></ul>',
                stepFunction: async (editor) => {
                    await insertText(editor, "/");
                    await insertText(editor, "Heading");
                    await animationFrame();
                    await press("Enter");
                    deleteBackward(editor);
                    deleteBackward(editor);
                },
                contentAfter: "<ul><li>abc[]</li></ul>",
            });
        });
    });

    describe("Merging different types of elements", () => {
        test("should merge a paragraph with text into a paragraph with text", async () => {
            await testEditor({
                contentBefore: "<p>ab</p><p>[]cd</p>",
                stepFunction: deleteBackward,
                contentAfter: "<p>ab[]cd</p>",
            });
        });

        test("should merge a paragraph with formated text into a paragraph with text", async () => {
            await testEditor({
                contentBefore: "<p>aa</p><p>[]a<i>bbb</i></p>",
                stepFunction: deleteBackward,
                contentAfter: "<p>aa[]a<i>bbb</i></p>",
            });
        });

        test("should merge a paragraph with text into a heading1 with text", async () => {
            await testEditor({
                contentBefore: "<h1>ab</h1><p>[]cd</p>",
                stepFunction: deleteBackward,
                contentAfter: "<h1>ab[]cd</h1>",
            });
        });

        test("should merge an empty paragraph into a heading1 with text", async () => {
            await testEditor({
                contentBefore: "<h1>ab</h1><p>[]<br></p>",
                stepFunction: deleteBackward,
                contentAfter: "<h1>ab[]</h1>",
            });
            await testEditor({
                contentBefore: "<h1>ab</h1><p><br>[]</p>",
                stepFunction: deleteBackward,
                contentAfter: "<h1>ab[]</h1>",
            });
        });

        test("should remove empty paragraph (keeping the heading)", async () => {
            await testEditor({
                contentBefore: "<p><br></p><h1>[]ab</h1>",
                stepFunction: deleteBackward,
                contentAfter: "<h1>[]ab</h1>",
            });
        });

        test("should merge a text preceding a paragraph (removing the paragraph)", async () => {
            await testEditor({
                contentBefore: "<div>ab<p>[]cd</p></div>",
                stepFunction: deleteBackward,
                contentAfter: "<div>ab[]cd</div>",
            });
            await testEditor({
                contentBefore: "<div>ab<p>[]cd</p>ef</div>",
                stepFunction: deleteBackward,
                contentAfter: "<div>ab[]cd<br>ef</div>",
            });
        });
    });

    describe("With attributes", () => {
        test("should remove paragraph with class", async () => {
            await testEditor({
                contentBefore: '<p class="a"><br></p><p>[]abc</p>',
                stepFunction: deleteBackward,
                contentAfter: "<p>[]abc</p>",
            });
        });

        test("should merge two paragraphs with spans of same classes", async () => {
            await testEditor({
                contentBefore: '<p><span class="a">ab</span></p><p><span class="a">[]cd</span></p>',
                stepFunction: deleteBackward,
                contentAfter: '<p><span class="a">ab[]cd</span></p>',
            });
        });

        test("should merge two paragraphs with spans of different classes without merging the spans", async () => {
            await testEditor({
                contentBefore: '<p><span class="a">ab</span></p><p><span class="b">[]cd</span></p>',
                stepFunction: deleteBackward,
                contentAfter: '<p><span class="a">ab[]</span><span class="b">cd</span></p>',
            });
        });

        test("should merge two paragraphs of different classes, each containing spans of the same class", async () => {
            await testEditor({
                contentBefore:
                    '<p class="a"><span class="b">ab</span></p><p class="c"><span class="b">[]cd</span></p>',
                stepFunction: deleteBackward,
                contentAfter: '<p class="a"><span class="b">ab[]cd</span></p>',
            });
        });

        test("should merge two paragraphs of different classes, each containing spans of different classes without merging the spans", async () => {
            await testEditor({
                contentBefore:
                    '<p class="a"><span class="b">ab</span></p><p class="c"><span class="d">[]cd</span></p>',
                stepFunction: deleteBackward,
                contentAfter:
                    '<p class="a"><span class="b">ab[]</span><span class="d">cd</span></p>',
            });
        });

        test("should delete a line break between two spans with bold and merge these formats", async () => {
            await testEditor({
                contentBefore:
                    '<p><span class="a"><b>ab</b></span><br><span class="a"><b>[]cd</b></span></p>',
                stepFunction: deleteBackward,
                contentAfter: '<p><span class="a"><b>ab[]cd</b></span></p>',
            });
        });

        test("should delete a character in a span with bold, then a line break between two spans with bold and merge these formats", async () => {
            await testEditor({
                contentBefore:
                    '<p><span class="a"><b>ab<br></b></span><br><span class="a"><b>c[]de</b></span></p>',
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                    deleteBackward(editor);
                },
                contentAfter: '<p><span class="a"><b>ab<br>[]de</b></span></p>',
            });
        });
    });

    describe("Nested editable zone (inside contenteditable=false element)", () => {
        test("should not remove the uneditable nesting zone nor the editable nested zone if the last element of the nested zone is empty", async () => {
            await testEditor({
                contentBefore: unformat(`
                        <div contenteditable="false">
                            <div contenteditable="true">
                                <p>[]<br></p>
                            </div>
                        </div>
                    `),
                stepFunction: deleteBackward,
                contentAfter: unformat(`
                        <div contenteditable="false">
                            <div contenteditable="true">
                                <p>[]<br></p>
                            </div>
                        </div>
                    `),
            });
        });

        test("should not remove the uneditable nesting zone nor the editable nested zone even if there is a paragraph after", async () => {
            await testEditor({
                contentBefore: unformat(`
                        <div contenteditable="false">
                            <div contenteditable="true">
                                <p>[]<br></p>
                            </div>
                        </div>
                        <p>content</p>
                    `),
                stepFunction: deleteBackward,
                contentAfter: unformat(`
                        <div contenteditable="false">
                            <div contenteditable="true">
                                <p>[]<br></p>
                            </div>
                        </div>
                        <p>content</p>
                    `),
            });
        });

        test("should not remove the uneditable nesting zone nor the editable nested zone if the last element of the nested zone is not empty", async () => {
            await testEditor({
                contentBefore: unformat(`
                        <div contenteditable="false">
                            <div contenteditable="true">
                                <p>[]content</p>
                            </div>
                        </div>
                    `),
                stepFunction: deleteBackward,
                contentAfter: unformat(`
                        <div contenteditable="false">
                            <div contenteditable="true">
                                <p>[]content</p>
                            </div>
                        </div>
                    `),
            });
        });

        test("should remove the uneditable nesting zone from the outside", async () => {
            await testEditor({
                contentBefore: unformat(`
                        <div contenteditable="false">
                            <div contenteditable="true">
                                <p>content</p>
                            </div>
                        </div>
                        <p>[]content</p>
                    `),
                stepFunction: deleteBackward,
                contentAfter: unformat(`
                        <p>[]content</p>
                    `),
            });
        });
    });

    describe("POC extra tests", () => {
        test("should delete an unique space between letters", async () => {
            await testEditor({
                contentBefore: "<p>ab []cd</p>",
                stepFunction: deleteBackward,
                contentAfter: "<p>ab[]cd</p>",
            });
        });

        test("should delete the first character in a paragraph (2)", async () => {
            await testEditor({
                contentBefore: "<p>a[] bc</p>",
                stepFunction: deleteBackward,
                contentAfter: "<p>[]&nbsp;bc</p>",
            });
        });

        test("should delete a space", async () => {
            await testEditor({
                contentBefore: "<p>ab [] de</p>",
                stepFunction: deleteBackward,
                contentAfter: "<p>ab[]de</p>",
            });
        });

        test("should delete a one letter word followed by visible space (start of block)", async () => {
            await testEditor({
                contentBefore: "<p>a[] b</p>",
                stepFunction: deleteBackward,
                contentAfter: "<p>[]&nbsp;b</p>",
            });
            await testEditor({
                contentBefore: "<p>[a] b</p>",
                stepFunction: deleteBackward,
                contentAfter: "<p>[]&nbsp;b</p>",
            });
        });

        test("should delete a one letter word surrounded by visible space", async () => {
            await testEditor({
                contentBefore: "<p>ab c[] de</p>",
                stepFunction: deleteBackward,
                contentAfter: "<p>ab []&nbsp;de</p>",
            });
            await testEditor({
                contentBefore: "<p>ab [c] de</p>",
                stepFunction: deleteBackward,
                contentAfter: "<p>ab []&nbsp;de</p>",
            });
        });

        test("should delete a one letter word preceded by visible space (end of block)", async () => {
            await testEditor({
                contentBefore: "<p>a b[]</p>",
                stepFunction: deleteBackward,
                contentAfter: "<p>a&nbsp;[]</p>",
            });
            await testEditor({
                contentBefore: "<p>a [b]</p>",
                stepFunction: deleteBackward,
                contentAfter: "<p>a&nbsp;[]</p>",
            });
        });

        test("should delete an empty paragraph in a table cell", async () =>
            await testEditor({
                contentBefore:
                    "<table><tbody><tr><td><p>a<br></p><p>[]<br></p></td></tr></tbody></table>",
                stepFunction: deleteBackward,
                contentAfter: "<table><tbody><tr><td><p>a[]</p></td></tr></tbody></table>",
            }));

        test("should fill empty block with a <br>", async () => {
            await testEditor({
                contentBefore: "<p>a[]</p>",
                stepFunction: deleteBackward,
                contentAfter: "<p>[]<br></p>",
            });
            await testEditor({
                contentBefore: "<p><img>[]</p>",
                stepFunction: deleteBackward,
                contentAfter: "<p>[]<br></p>",
            });
        });

        test("should merge a paragraph with text into a paragraph with text removing spaces", async () => {
            await testEditor({
                contentBefore: "<p>ab   </p>    <p>   []cd</p>",
                stepFunction: deleteBackward,
                // This is a tricky case: the spaces after ab are
                // visible on Firefox but not on Chrome... to be
                // consistent we enforce the space removal here but
                // maybe not a good idea... see next case ->
                contentAfter: "<p>ab[]cd</p>",
            });
            await testEditor({
                contentBefore: "<p>ab   <br></p>    <p>   []cd</p>",
                stepFunction: deleteBackward,
                // This is the same visible case as the one above. The
                // difference is that here the space after ab is visible
                // on both Firefox and Chrome, so it should stay
                // visible.
                contentAfter: "<p>ab   []cd</p>",
            });
        });

        test("should remove a br and remove following spaces", async () => {
            await testEditor({
                contentBefore: "<p>ab<br><b>[]   </b>cd</p>",
                stepFunction: deleteBackward,
                contentAfter: "<p>ab[]cd</p>",
            });
            await testEditor({
                contentBefore: "<p>ab<br><b>[]   x</b>cd</p>",
                stepFunction: deleteBackward,
                contentAfter: "<p>ab[]<b>x</b>cd</p>",
            });
        });

        test("should ignore empty inline node between blocks being merged", async () => {
            await testEditor({
                contentBefore: "<div><p>abc</p><i> </i><p>[]def</p></div>",
                stepFunction: deleteBackward,
                contentAfter: "<div><p>abc[]def</p></div>",
            });
        });

        test("should merge in nested paragraphs and remove invisible inline content", async () => {
            await testEditor({
                contentBefore:
                    '<custom-block style="display: block;"><p>ab</p>    </custom-block><p>[]c</p>',
                stepFunction: deleteBackward,
                contentAfter: '<custom-block style="display: block;"><p>ab[]c</p></custom-block>',
            });
            await testEditor({
                contentBefore:
                    '<custom-block style="display: block;"><p>ab</p> <i> </i> </custom-block><p>[]c</p>',
                stepFunction: deleteBackward,
                contentAfter: '<custom-block style="display: block;"><p>ab[]c</p></custom-block>',
            });
        });

        test("should not merge in nested blocks if inline content afterwards", async () => {
            await testEditor({
                contentBefore:
                    '<custom-block style="display: block;"><p>ab</p>de</custom-block><p>[]fg</p>',
                stepFunction: deleteBackward,
                contentAfter:
                    '<custom-block style="display: block;"><p>ab</p>de[]fg</custom-block>',
            });
            await testEditor({
                contentBefore:
                    '<custom-block style="display: block;"><p>ab</p><img></custom-block><p>[]fg</p>',
                stepFunction: deleteBackward,
                contentAfter:
                    '<custom-block style="display: block;"><p>ab</p><img>[]fg</custom-block>',
            });
        });

        test("should move paragraph content to empty block", async () => {
            await testEditor({
                contentBefore: "<p>abc</p><h1><br></h1><p>[]def</p>",
                stepFunction: deleteBackward,
                contentAfter: "<p>abc</p><p>[]def</p>",
            });
        });

        test("should remove only one br between contents", async () => {
            await testEditor({
                contentBefore: "<p>abc<br>[]<br>def</p>",
                stepFunction: deleteBackward,
                contentAfter: "<p>abc[]<br>def</p>",
            });
        });

        test("should remove an empty block instead of merging it", async () => {
            await testEditor({
                contentBefore: "<p><br></p><p>[]<br></p>",
                stepFunction: deleteBackward,
                contentAfter: "<p>[]<br></p>",
            });
        });

        test("should not remove a table without selecting it", async () => {
            await testEditor({
                contentBefore: unformat(
                    `<p>ab</p>
                        <table><tbody>
                            <tr><td>cd</td><td>ef</td></tr>
                            <tr><td>gh</td><td>ij</td></tr>
                        </tbody></table>
                        <p>[]kl</p>`
                ),
                stepFunction: deleteBackward,
                contentAfter: unformat(
                    `<p>ab</p>
                        <table><tbody>
                            <tr><td>cd</td><td>ef</td></tr>
                            <tr><td>gh</td><td>ij</td></tr>
                        </tbody></table>
                        <p>[]kl</p>`
                ),
            });
        });

        test("should not merge a table into its previous sibling", async () => {
            await testEditor({
                contentBefore: unformat(
                    `<p>ab</p>
                        <table><tbody>
                            <tr><td>[]cd</td><td>ef</td></tr>
                            <tr><td>gh</td><td>ij</td></tr>
                        </tbody></table>
                        <p>kl</p>`
                ),
                stepFunction: deleteBackward,
                contentAfter: unformat(
                    `<p>ab</p>
                        <table><tbody>
                            <tr><td>[]cd</td><td>ef</td></tr>
                            <tr><td>gh</td><td>ij</td></tr>
                        </tbody></table>
                        <p>kl</p>`
                ),
            });
        });

        test("should delete an image that is displayed as a block", async () => {
            await testEditor({
                // @phoenix content adapted to make it valid html
                contentBefore: unformat(`<div>a[b<img style="display: block;">c]d</div>`),
                stepFunction: deleteBackward,
                contentAfter: unformat(`<div>a[]d</div>`),
            });
        });
    });
});

describe("Selection not collapsed", () => {
    test("ZWS : should keep inline block", async () => {
        await testEditor({
            contentBefore: '<div><p>ab <span class="style">[c]</span> d</p></div>',
            stepFunction: async (editor) => {
                deleteBackward(editor);
            },
            contentAfterEdit:
                '<div><p>ab <span class="style" data-oe-zws-empty-inline="">[]\u200B</span> d</p></div>',
            contentAfter: '<div><p>ab <span class="style">[]\u200B</span> d</p></div>',
        });
        await testEditor({
            contentBefore: '<div><p>ab <span class="style">[c]</span> d</p></div>',
            stepFunction: async (editor) => {
                deleteBackward(editor);
                await insertText(editor, "x");
            },
            contentAfterEdit: '<div><p>ab <span class="style">x[]</span> d</p></div>',
            contentAfter: '<div><p>ab <span class="style">x[]</span> d</p></div>',
        });
        await testEditor({
            contentBefore: "<div><p>ab <span>[c]</span> d</p></div>",
            stepFunction: async (editor) => {
                deleteBackward(editor);
            },
            contentAfterEdit:
                '<div><p>ab <span data-oe-zws-empty-inline="">[]\u200B</span> d</p></div>',
            contentAfter: "<div><p>ab []&nbsp;d</p></div>",
        });
        await testEditor({
            contentBefore: '<div><p>ab<span class="style">[c]</span>d</p></div>',
            stepFunction: async (editor) => {
                deleteBackward(editor);
                await insertText(editor, "x");
            },
            contentAfterEdit: '<div><p>ab<span class="style">x[]</span>d</p></div>',
            contentAfter: '<div><p>ab<span class="style">x[]</span>d</p></div>',
        });
        await testEditor({
            contentBefore: '<div><p>ab <span class="style">[cde]</span> f</p></div>',
            stepFunction: async (editor) => {
                deleteBackward(editor);
                await insertText(editor, "x");
            },
            contentAfterEdit: '<div><p>ab <span class="style">x[]</span> f</p></div>',
            contentAfter: '<div><p>ab <span class="style">x[]</span> f</p></div>',
        });
    });

    test("should merge node correctly (1)", async () => {
        await testEditor({
            contentBefore: '<div>a<span class="a">b[c</span><p>d]e</p>f<br>g</div>',
            stepFunction: deleteBackward,
            // FIXME ?? : Maybe this should bing the content inside the <p>
            // Instead of removing the <p>,
            // ex : <div><p>a<span class="a">b[]</span>e</p>f<br>g</div>
            contentAfter: '<div>a<span class="a">b[]</span>e<br>f<br>g</div>',
        });
    });

    test("should merge node correctly (2)", async () => {
        await testEditor({
            contentBefore: '<div>a<p>b[c</p><span class="a">d]e</span>f<p>xxx</p></div>',
            stepFunction: deleteBackward,
            contentAfter: '<div>a<p>b[]<span class="a">e</span>f</p><p>xxx</p></div>',
        });
    });

    test("should delete part of the text within a paragraph (backward, forward selection)", async () => {
        // Forward selection
        await testEditor({
            contentBefore: "<p>ab[cd]ef</p>",
            stepFunction: deleteBackward,
            contentAfter: "<p>ab[]ef</p>",
        });
    });
    test("should delete part of the text within a paragraph (backward, backward selection)", async () => {
        // Backward selection
        await testEditor({
            contentBefore: "<p>ab]cd[ef</p>",
            stepFunction: deleteBackward,
            contentAfter: "<p>ab[]ef</p>",
        });
    });

    test("should delete across two paragraphs", async () => {
        // Forward selection
        await testEditor({
            contentBefore: "<p>ab[cd</p><p>ef]gh</p>",
            stepFunction: deleteBackward,
            contentAfter: "<p>ab[]gh</p>",
        });
        // Backward selection
        await testEditor({
            contentBefore: "<p>ab]cd</p><p>ef[gh</p>",
            stepFunction: deleteBackward,
            contentAfter: "<p>ab[]gh</p>",
        });
    });

    test("should delete part of the text across two paragraphs (backward, forward selection)", async () => {
        await testEditor({
            contentBefore: "<div>a<p>b[c</p><p>d]e</p>f</div>",
            stepFunction: deleteBackward,
            contentAfter: "<div>a<p>b[]e</p>f</div>",
        });
    });
    test("should delete part of the text across two paragraphs (backward, backward selection)", async () => {
        await testEditor({
            contentBefore: "<div>a<p>b]c</p><p>d[e</p>f</div>",
            stepFunction: deleteBackward,
            contentAfter: "<div>a<p>b[]e</p>f</div>",
        });
    });

    test("should delete all the text in a paragraph", async () => {
        // Forward selection
        await testEditor({
            contentBefore: "<p>[abc]</p>",
            stepFunction: deleteBackward,
            contentAfter: "<p>[]<br></p>",
        });
        // Backward selection
        await testEditor({
            contentBefore: "<p>]abc[</p>",
            stepFunction: deleteBackward,
            contentAfter: "<p>[]<br></p>",
        });
    });

    test("should delete a complex selection accross format nodes and multiple paragraphs", async () => {
        // Forward selection
        await testEditor({
            contentBefore: "<p><b>ab[cd</b></p><p><b>ef<br>gh</b>ij<i>kl]</i>mn</p>",
            stepFunction: deleteBackward,
            contentAfter: "<p><b>ab[]</b>mn</p>",
        });
        await testEditor({
            contentBefore: "<p><b>ab[cd</b></p><p><b>ef<br>gh</b>ij<i>k]l</i>mn</p>",
            stepFunction: deleteBackward,
            contentAfter: "<p><b>ab[]</b><i>l</i>mn</p>",
        });
        // Backward selection
        await testEditor({
            contentBefore: "<p><b>ab]cd</b></p><p><b>ef<br>gh</b>ij<i>kl[</i>mn</p>",
            stepFunction: deleteBackward,
            contentAfter: "<p><b>ab[]</b>mn</p>",
        });
        await testEditor({
            contentBefore: "<p><b>ab]cd</b></p><p><b>ef<br>gh</b>ij<i>k[l</i>mn</p>",
            stepFunction: deleteBackward,
            contentAfter: "<p><b>ab[]</b><i>l</i>mn</p>",
        });
    });

    //
    test("should delete all contents of a complex DOM with format nodes and multiple paragraphs (backward, forward selection)", async () => {
        await testEditor({
            contentBefore: "<p><b>[abcd</b></p><p><b>ef<br>gh</b>ij<i>kl</i>mn]</p>",
            stepFunction: deleteBackward,
            contentAfter: "<p>[]<br></p>",
        });
    });

    test("should delete all contents of a complex DOM with format nodes and multiple paragraphs (backward, backward selection)", async () => {
        await testEditor({
            contentBefore: "<p><b>]abcd</b></p><p><b>ef<br>gh</b>ij<i>kl</i>mn[</p>",
            stepFunction: deleteBackward,
            contentAfter: "<p>[]<br></p>",
        });
    });

    test("should delete a selection accross a heading1 and a paragraph", async () => {
        // Forward selection
        await testEditor({
            contentBefore: "<h1>ab [cd</h1><p>ef]gh</p>",
            stepFunction: deleteBackward,
            contentAfter: "<h1>ab []gh</h1>",
        });
        // Backward selection
        await testEditor({
            contentBefore: "<h1>ab ]cd</h1><p>ef[gh</p>",
            stepFunction: deleteBackward,
            contentAfter: "<h1>ab []gh</h1>",
        });
    });

    test("should delete a selection from the beginning of a heading1 with a format to the middle of a paragraph", async () => {
        // Forward selection
        await testEditor({
            contentBefore: "<h1><b>[abcd</b></h1><p>ef]gh1</p>",
            stepFunction: deleteBackward,
            contentAfter: "<p>[]gh1</p>",
        });
        await testEditor({
            contentBefore: "<h1>[<b>abcd</b></h1><p>ef]gh2</p>",
            stepFunction: deleteBackward,
            contentAfter: "<p>[]gh2</p>",
        });
        // Backward selection
        await testEditor({
            contentBefore: "<h1><b>]abcd</b></h1><p>ef[gh3</p>",
            stepFunction: deleteBackward,
            contentAfter: "<p>[]gh3</p>",
        });
        await testEditor({
            contentBefore: "<h1>]<b>abcd</b></h1><p>ef[gh4</p>",
            stepFunction: deleteBackward,
            contentAfter: "<p>[]gh4</p>",
        });
    });

    test("should delete a heading (triple click backspace) (1)", async () => {
        const { editor, el } = await setupEditor("<h1>abc</h1><p>def</p>", {});
        let release = await splitTripleClick(el.querySelector("h1"));
        // Chrome puts the cursor at the start of next sibling
        expect(getContent(el)).toBe("<h1>[abc</h1><p>]def</p>");
        await release();
        // The Editor corrects it on selection change
        expect(getContent(el)).toBe("<h1>[abc]</h1><p>def</p>");
        release = await splitTripleClick(el.querySelector("h1"));
        // Chrome puts the cursor at the start of next sibling
        expect(getContent(el)).toBe("<h1>[abc</h1><p>]def</p>");
        await release();
        // The Editor corrects it repeatedly on selection change
        expect(getContent(el)).toBe("<h1>[abc]</h1><p>def</p>");
        deleteBackward(editor);
        expect(getContent(el)).toBe(
            '<h1 placeholder="Heading 1" class="o-we-hint">[]<br></h1><p>def</p>'
        );
    });

    test("should delete a heading (triple click backspace) (2)", async () => {
        const { editor, el } = await setupEditor("<h1>abc</h1><p><br></p><p>def</p>", {});
        const release = await splitTripleClick(el.querySelector("h1"));
        // Chrome puts the cursor at the start of next sibling
        expect(getContent(el)).toBe("<h1>[abc</h1><p>]<br></p><p>def</p>");
        await release();
        // The Editor corrects it on selection change
        expect(getContent(el)).toBe("<h1>[abc]</h1><p><br></p><p>def</p>");
        deleteBackward(editor);
        expect(getContent(el)).toBe(
            '<h1 placeholder="Heading 1" class="o-we-hint">[]<br></h1><p><br></p><p>def</p>'
        );
    });

    test("should delete last character of paragraph and merge the two p elements", async () => {
        await testEditor({
            contentBefore: "<p>ab[c</p><p>]def</p>",
            stepFunction: deleteBackward,
            contentAfter: "<p>ab[]def</p>",
        });
        await testEditor({
            contentBefore: "<p>ab[c</p><p>]<br></p><p>def</p>",
            stepFunction: deleteBackward,
            contentAfter: "<p>ab[]</p><p>def</p>",
        });
    });

    test("should delete first character of paragraph, as well as selected paragraph break", async () => {
        await testEditor({
            contentBefore: "<p>abc[</p><p>d]ef</p>",
            stepFunction: deleteBackward,
            contentAfter: "<p>abc[]ef</p>",
        });
    });

    test("should remove a fully selected table", async () => {
        await testEditor({
            contentBefore: unformat(
                `<p>a[b</p>
                    <table><tbody>
                        <tr><td>cd</td><td>ef</td></tr>
                        <tr><td>gh</td><td>ij</td></tr>
                    </tbody></table>
                    <p>k]l</p>`
            ),
            stepFunction: deleteBackward,
            contentAfter: "<p>a[]l</p>",
        });
    });

    test("should remove a fully selected nested table", async () => {
        await testEditor({
            contentBefore: unformat(
                `<p>a[b</p>
                    <table><tbody>
                        <tr>
                            <td>
                                <table><tbody>
                                    <tr><td><br></td><td><br></td></tr>
                                    <tr><td><br></td><td><br></td></tr>
                                </tbody></table>
                            </td>
                        <td>ef</td></tr>
                        <tr><td>gh</td><td>ij</td></tr>
                    </tbody></table>
                    <p>k]l</p>`
            ),
            stepFunction: deleteBackward,
            contentAfter: "<p>a[]l</p>",
        });
    });

    test("should delete nothing when in an empty table cell", async () => {
        await testEditor({
            contentBefore:
                "<table><tbody><tr><td>abc</td><td>[]<br></td><td>abc</td></tr></tbody></table>",
            stepFunction: deleteBackward,
            contentAfter:
                "<table><tbody><tr><td>abc</td><td>[]<br></td><td>abc</td></tr></tbody></table>",
        });
    });

    test("should delete nothing when in an empty paragraph in a table cell", async () => {
        await testEditor({
            contentBefore:
                "<table><tbody><tr><td>abc</td><td><p>[]<br></p></td></tr></tbody></table>",
            stepFunction: deleteBackward,
            contentAfter:
                "<table><tbody><tr><td>abc</td><td><p>[]<br></p></td></tr></tbody></table>",
        });
    });

    test("should only remove the text content of cells in a partly selected table", async () => {
        await testEditor({
            contentBefore: unformat(
                `<table><tbody>
                        <tr><td>cd</td><td class="o_selected_td">e[f</td><td>gh</td></tr>
                        <tr><td>ij</td><td class="o_selected_td">k]l</td><td>mn</td></tr>
                        <tr><td>op</td><td>qr</td><td>st</td></tr>
                    </tbody></table>`
            ),
            stepFunction: deleteBackward,
            contentAfter: unformat(
                `<table><tbody>
                        <tr><td>cd</td><td><p>[]<br></p></td><td>gh</td></tr>
                        <tr><td>ij</td><td><p><br></p></td><td>mn</td></tr>
                        <tr><td>op</td><td>qr</td><td>st</td></tr>
                    </tbody></table>`
            ),
        });
    });

    test("should remove a row in a partly selected table", async () => {
        await testEditor({
            contentBefore: unformat(
                `<table><tbody>
                    <tr><td class="o_selected_td">[ab</td><td class="o_selected_td">cd]</td></tr>
                    <tr><td>ef</td><td>gh</td></tr>
                </tbody></table>`
            ),
            stepFunction: deleteBackward,
            contentAfter: unformat(
                `<table><tbody>
                    <tr><td>[]ef</td><td>gh</td></tr>
                </tbody></table>`
            ),
        });
    });

    test("should remove a column in a partly selected table", async () => {
        await testEditor({
            contentBefore: unformat(
                `<table><tbody>
                    <tr><td class="o_selected_td">[ab</td> <td>cd</td></tr>
                    <tr><td class="o_selected_td">ef]</td> <td>gh</td></tr>
                </tbody></table>`
            ),
            stepFunction: deleteBackward,
            contentAfter: unformat(
                `<table><tbody>
                    <tr><td>[]cd</td></tr>
                    <tr><td>gh</td></tr>
                </tbody></table>`
            ),
        });
    });

    test("should remove some text and a table (even if the table is partly selected)", async () => {
        await testEditor({
            contentBefore: unformat(
                `<p>a[b</p>
                    <table><tbody>
                        <tr><td>cd</td><td>ef</td></tr>
                        <tr><td>g]h</td><td>ij</td></tr>
                    </tbody></table>
                    <p>kl</p>`
            ),
            stepFunction: deleteBackward,
            contentAfter: unformat(
                `<p>a[]</p>
                    <p>kl</p>`
            ),
        });
    });

    test("should remove a table and some text (even if the table is partly selected)", async () => {
        await testEditor({
            contentBefore: unformat(
                `<p>ab</p>
                    <table><tbody>
                        <tr><td>cd</td><td>ef</td></tr>
                        <tr><td>gh</td><td>i[j</td></tr>
                    </tbody></table>
                    <p>k]l</p>`
            ),
            stepFunction: deleteBackward,
            contentAfter: unformat(
                `<p>ab</p>
                    <p>[]l</p>`
            ),
        });
    });

    test("should remove some text, a table and some more text", async () => {
        await testEditor({
            contentBefore: unformat(
                `<p>a[b</p>
                    <table><tbody>
                        <tr><td>cd</td><td>ef</td></tr>
                        <tr><td>gh</td><td>ij</td></tr>
                    </tbody></table>
                    <p>k]l</p>`
            ),
            stepFunction: deleteBackward,
            contentAfter: `<p>a[]l</p>`,
        });
    });

    test("should remove a selection of several tables", async () => {
        await testEditor({
            contentBefore: unformat(
                `<table><tbody>
                        <tr><td>cd</td><td>e[f</td></tr>
                        <tr><td>gh</td><td>ij</td></tr>
                    </tbody></table>
                    <table><tbody>
                        <tr><td>cd</td><td>ef</td></tr>
                        <tr><td>gh</td><td>ij</td></tr>
                    </tbody></table>
                    <table><tbody>
                        <tr><td>cd</td><td>e]f</td></tr>
                        <tr><td>gh</td><td>ij</td></tr>
                    </tbody></table>`
            ),
            stepFunction: deleteBackward,
            contentAfter: `<p>[]<br></p>`,
        });
    });

    test("should remove a selection including several tables", async () => {
        await testEditor({
            contentBefore: unformat(
                `<p>0[1</p>
                    <table><tbody>
                        <tr><td>cd</td><td>ef</td></tr>
                        <tr><td>gh</td><td>ij</td></tr>
                    </tbody></table>
                    <p>23</p>
                    <table><tbody>
                        <tr><td>cd</td><td>ef</td></tr>
                        <tr><td>gh</td><td>ij</td></tr>
                    </tbody></table>
                    <p>45</p>
                    <table><tbody>
                        <tr><td>cd</td><td>ef</td></tr>
                        <tr><td>gh</td><td>ij</td></tr>
                    </tbody></table>
                    <p>67]</p>`
            ),
            stepFunction: deleteBackward,
            contentAfter: `<p>0[]</p>`,
        });
    });

    test("should remove everything, including several tables", async () => {
        await testEditor({
            contentBefore: unformat(
                `<p>[01</p>
                    <table><tbody>
                        <tr><td>cd</td><td>ef</td></tr>
                        <tr><td>gh</td><td>ij</td></tr>
                    </tbody></table>
                    <p>23</p>
                    <table><tbody>
                        <tr><td>cd</td><td>ef</td></tr>
                        <tr><td>gh</td><td>ij</td></tr>
                    </tbody></table>
                    <p>45</p>
                    <table><tbody>
                        <tr><td>cd</td><td>ef</td></tr>
                        <tr><td>gh</td><td>ij</td></tr>
                    </tbody></table>
                    <p>67]</p>`
            ),
            stepFunction: deleteBackward,
            contentAfter: `<p>[]<br></p>`,
        });
    });

    test("should do nothing with selection before table and start of middle cell", async () => {
        await testEditor({
            contentBefore: unformat(
                `[<table><tbody>
                    <tr><td><br></td><td><br></td></tr>
                    <tr><td><br></td><td>]<br></td></tr>
                </tbody></table>`
            ),
            contentBeforeEdit: unformat(
                `[<table class="o_selected_table"><tbody>
                    <tr><td class="o_selected_td"><br></td><td class="o_selected_td"><br></td></tr>
                    <tr><td class="o_selected_td"><br></td><td class="o_selected_td">]<br></td></tr>
                </tbody></table>`
            ),
            stepFunction: deleteBackward,
            contentAfter: unformat("<p>[]<br></p>"),
        });
    });

    test("should empty an inline unremovable but remain in it", async () => {
        await testEditor({
            contentBefore: '<p>ab<b class="oe_unremovable">[cd]</b>ef</p>',
            stepFunction: deleteBackward,
            contentAfter: '<p>ab<b class="oe_unremovable">[]\u200B</b>ef</p>',
        });
    });

    test("should delete if first element and append in paragraph", async () => {
        await testEditor({
            contentBefore: `<blockquote><br>[]</blockquote>`,
            stepFunction: deleteBackward,
            contentAfter: `<p>[]<br></p>`,
        });
        await testEditor({
            contentBefore: `<h1><br>[]</h1>`,
            stepFunction: deleteBackward,
            contentAfter: `<p>[]<br></p>`,
        });
        await testEditor({
            contentBefore: `<h4><br>[]</h4>`,
            stepFunction: deleteBackward,
            contentAfter: `<p>[]<br></p>`,
        });
    });

    test("should not delete the block and appends a paragraph if the element has textContent ", async () => {
        await testEditor({
            contentBefore: `<h1>[]abc</h1>`,
            stepFunction: deleteBackward,
            contentAfter: `<h1>[]abc</h1>`,
        });
        await testEditor({
            contentBefore: `<h1><font style="background-color: rgb(255, 0, 0);">[]abc</font></h1>`,
            stepFunction: deleteBackward,
            contentAfter: `<h1><font style="background-color: rgb(255, 0, 0);">[]abc</font></h1>`,
        });
        await testEditor({
            contentBefore: `<table><tbody><tr><td><h1>[]ab</h1></td><td>cd</td><td>ef</td></tr><tr><td><br></td><td><br></td><td><br></td></tr></tbody></table>`,
            stepFunction: deleteBackward,
            contentAfter: `<table><tbody><tr><td><h1>[]ab</h1></td><td>cd</td><td>ef</td></tr><tr><td><br></td><td><br></td><td><br></td></tr></tbody></table>`,
        });
    });

    test("should not delete styling nodes if not selected", async () => {
        // deleteBackward selection
        await testEditor({
            contentBefore: '<p>a<span class="style-class">[bcde]</span>f</p>',
            stepFunction: deleteBackward,
            contentAfter: '<p>a<span class="style-class">[]\u200B</span>f</p>',
        });
    });

    test("should delete styling nodes when delete if empty with space around inline (backward)", async () => {
        // deleteBackward selection
        await testEditor({
            contentBefore: '<p>ab <span class="style-class">[cd]</span> ef</p>',
            stepFunction: async (editor) => {
                deleteBackward(editor);
                deleteBackward(editor);
            },
            contentAfter: "<p>ab[] ef</p>",
        });
    });
    test("should delete styling nodes when delete if empty (backward)", async () => {
        await testEditor({
            contentBefore: '<p>uv<span class="style-class">[wx]</span>yz</p>',
            stepFunction: async (editor) => {
                deleteBackward(editor);
                deleteBackward(editor);
            },
            contentAfter: "<p>u[]yz</p>",
        });
    });

    test("should transform the last space of a container to an &nbsp; after removing the last word through deleteRange", async () => {
        await testEditor({
            contentBefore: `<p>a [b]</p>`,
            stepFunction: async (editor) => {
                deleteBackward(editor);
            },
            contentAfter: `<p>a&nbsp;[]</p>`,
        });
    });

    describe("Nested editable zone (inside contenteditable=false element)", () => {
        test("should extend the range to fully include contenteditable=false that are partially selected at the end of the range", async () => {
            await testEditor({
                contentBefore: unformat(`
                        <p>before[o</p>
                        <div contenteditable="false">
                            <div contenteditable="true"><p>intruder]</p></div>
                        </div>
                        <p>after</p>`),
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                },
                contentAfter: unformat(`
                        <p>before[]</p><p>after</p>`),
            });
        });

        // @todo @phoenix: review this spec. It should not merge, like the test above.
        test("should extend the range to fully include contenteditable=false that are partially selected at the start of the range", async () => {
            await testEditor({
                contentBefore: unformat(`
                        <p>before</p>
                        <div contenteditable="false">
                            <div contenteditable="true"><p>[intruder</p></div>
                        </div>
                        <p>o]after</p>`),
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                },
                contentAfter: unformat(`
                        <p>before[]after</p>`),
            });
        });

        test("should remove element which is contenteditable=true even if their parent is contenteditable=false", async () => {
            await testEditor({
                contentBefore: unformat(`
                        <p>before[o</p>
                        <div contenteditable="false">
                            <div contenteditable="true"><p>intruder</p></div>
                        </div>
                        <p>o]after</p>`),
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                },
                contentAfter: unformat(`
                        <p>before[]after</p>`),
            });
        });

        test("should remove empty paragraph and content from the second one", async () => {
            await testEditor({
                contentBefore: "<p>ab</p><p>[<br></p><p>d]ef</p>",
                stepFunction: deleteBackward,
                contentAfter: "<p>ab</p><p>[]ef</p>",
            });
        });

        test.todo("should not delete in contenteditable=false 1", async () => {
            await testEditor({
                contentBefore: `<p contenteditable="false">ab[cd]ef</p>`,
                stepFunction: deleteBackward,
                contentAfter: `<p contenteditable="false">ab[cd]ef</p>`,
            });
        });

        test.todo("should not delete in contenteditable=false 2", async () => {
            await testEditor({
                contentBefore: `<div contenteditable="false">
                                    <p>a[b</p>
                                    <p>cd</p>
                                    <p>e]f</p>
                                </div>`,
                stepFunction: deleteBackward,
                contentAfter: `<div contenteditable="false">
                                    <p>a[b</p>
                                    <p>cd</p>
                                    <p>e]f</p>
                                </div>`,
            });
        });

        test("should fill the inner editable with a P when all of its contents are removed", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <div contenteditable="false">
                        <div contenteditable="true">[<p>abc</p>]</div>
                    </div>`),
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                },
                contentAfter: unformat(`
                    <div contenteditable="false">
                        <div contenteditable="true"><p>[]<br></p></div>
                    </div>`),
            });
        });

        test("should fill the inner editable with a P when all of its contents are removed (2)", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <div contenteditable="false">
                        <div contenteditable="true">[<h1>abc</h1><p>def</p>]</div>
                    </div>`),
                stepFunction: async (editor) => {
                    deleteBackward(editor);
                },
                contentAfter: unformat(`
                    <div contenteditable="false">
                        <div contenteditable="true"><p>[]<br></p></div>
                    </div>`),
            });
        });
    });

    describe("Android Chrome", () => {
        beforeEach(() => {
            patchWithCleanup(browser.navigator, {
                userAgent:
                    "Mozilla/5.0 (Linux; Android 10; Pixel 3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Mobile Safari/537.36",
            });
        });

        // This simulates the sequence of events that happens in Android Chrome
        // when pressing backspace. Some random stuff might happen, and
        // `extraAction` can be used to simulate that.
        const backspaceAndroid = async (editor, { extraAction = null } = {}) => {
            const dispatch = (type, eventInit) =>
                manuallyDispatchProgrammaticEvent(editor.editable, type, eventInit);
            const selection = editor.document.getSelection();
            if (selection.isCollapsed) {
                selection.modify("extend", "backward", "character");
            }
            await dispatch("keydown", { key: "Unidentified" });
            await dispatch("beforeinput", { inputType: "deleteContentBackward" });
            // beforeinput event is not default preventable
            selection.getRangeAt(0).deleteContents();
            extraAction?.();
            await dispatch("input", { inputType: "deleteContentBackward" });
            await dispatch("keyup", { key: "Unidentified" });
        };

        test.tags("mobile");
        test("should merge paragraphs and put cursor between c and d", async () => {
            const { editor, el } = await setupEditor("<p>abc</p><p>[]def</p>");
            await backspaceAndroid(editor, {
                extraAction: async () => {
                    // Simulate what happens in Android Chrome for this particular
                    // case: after input, the cursor is moved one character to the
                    // right: <p>abcd[]ef</p>
                    await microTick();
                    const secondTextNode = el.querySelector("p").childNodes[1];
                    setSelection({ anchorNode: secondTextNode, anchorOffset: 1 });
                },
            });
            await tick(); // Wait for the selection change to be handled
            expect(getContent(el)).toBe("<p>abc[]def</p>");
        });

        test.tags("mobile");
        test("should revert random stuff done by chrome", async () => {
            const { editor, el } = await setupEditor("<p>abc[]</p>");
            await backspaceAndroid(editor, {
                extraAction: () =>
                    el.append(
                        editor.document.createTextNode("random changes that should be reverted")
                    ),
            });
            expect(getContent(el)).toBe("<p>ab[]</p>");
        });

        test.tags("mobile");
        test("should not break Gboard dictionary input", async () => {
            const { editor, el } = await setupEditor("<p>woonderf[]</p>");
            // Roughly as observed on Android Chrome with Gboard:
            // - selection change
            // - input deleteContentBackward
            // - input insertText
            const selection = editor.document.getSelection();
            for (let i = 0; i < 6; i++) {
                selection.modify("extend", "backward", "character");
            }
            await backspaceAndroid(editor);
            await insertText(editor, "nderful ");
            await tick(); // Wait for the selection change to be handled
            expect(getContent(el)).toBe("<p>wonderful []</p>");
        });
    });
});
