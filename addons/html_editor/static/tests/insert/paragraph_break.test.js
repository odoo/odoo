import { describe, test } from "@odoo/hoot";
import { testEditor } from "../_helpers/editor";
import { splitBlock } from "../_helpers/user_actions";

describe("Selection collapsed", () => {
    describe("Basic", () => {
        test("should duplicate an empty paragraph", async () => {
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                stepFunction: splitBlock,
                contentAfter: "<p><br></p><p>[]<br></p>",
            });
            // TODO this cannot actually be tested currently as a
            // backspace/delete in that case is not even detected
            // (no input event to rollback)
            // await testEditor({
            //     contentBefore: '<p>[<br>]</p>',
            //     stepFunction: splitBlock,
            //     contentAfter: '<p><br></p><p>[]<br></p>',
            // });
            await testEditor({
                contentBefore: "<p><br>[]</p>",
                stepFunction: splitBlock,
                contentAfter: "<p><br></p><p>[]<br></p>",
            });
        });

        test("should insert an empty paragraph before a paragraph", async () => {
            await testEditor({
                contentBefore: "<p>[]abc</p>",
                stepFunction: splitBlock,
                contentAfter: "<p><br></p><p>[]abc</p>",
            });
            await testEditor({
                contentBefore: "<p>[] abc</p>",
                stepFunction: splitBlock,
                // JW cAfter: '<p><br></p><p>[]abc</p>',
                contentAfter: "<p><br></p><p>[] abc</p>",
            });
        });

        test("should split a paragraph in two", async () => {
            await testEditor({
                contentBefore: "<p>ab[]cd</p>",
                stepFunction: splitBlock,
                contentAfter: "<p>ab</p><p>[]cd</p>",
            });
            await testEditor({
                contentBefore: "<p>ab []cd</p>",
                stepFunction: splitBlock,
                // The space is converted to a non-breaking
                // space so it is visible.
                contentAfter: "<p>ab&nbsp;</p><p>[]cd</p>",
            });
            await testEditor({
                contentBefore: "<p>ab[] cd</p>",
                stepFunction: splitBlock,
                // The space is converted to a non-breaking
                // space so it is visible.
                contentAfter: "<p>ab</p><p>[]&nbsp;cd</p>",
            });
        });

        test("should insert an empty paragraph after a paragraph", async () => {
            await testEditor({
                contentBefore: "<p>abc[]</p>",
                stepFunction: splitBlock,
                contentAfter: "<p>abc</p><p>[]<br></p>",
            });
            await testEditor({
                contentBefore: "<p>abc[] </p>",
                stepFunction: splitBlock,
                contentAfter: "<p>abc</p><p>[]<br></p>",
            });
        });
    });

    describe("Pre", () => {
        test("should insert a line break within the pre", async () => {
            await testEditor({
                contentBefore: "<pre>ab[]cd</pre>",
                stepFunction: splitBlock,
                contentAfter: "<pre>ab<br>[]cd</pre>",
            });
        });
        test("should insert a line break within the pre containing inline element", async () => {
            await testEditor({
                contentBefore: "<pre>a<strong>b[]c</strong>d</pre>",
                stepFunction: splitBlock,
                contentAfter: "<pre>a<strong>b<br>[]c</strong>d</pre>",
            });
        });
        test("should insert a line break within the pre containing inline elementd", async () => {
            await testEditor({
                contentBefore: "<pre><em>a<strong>b[]c</strong>d</em></pre>",
                stepFunction: splitBlock,
                contentAfter: "<pre><em>a<strong>b<br>[]c</strong>d</em></pre>",
            });
        });

        test("should insert a new paragraph after the pre", async () => {
            await testEditor({
                contentBefore: "<pre>abc[]</pre>",
                stepFunction: splitBlock,
                contentAfter: "<pre>abc</pre><p>[]<br></p>",
            });
        });
        test("should insert a new paragraph after the pre containing inline element", async () => {
            await testEditor({
                contentBefore: "<pre>ab<strong>c[]</strong></pre>",
                stepFunction: splitBlock,
                contentAfter: "<pre>ab<strong>c</strong></pre><p>[]<br></p>",
            });
        });
        test("should insert a new paragraph after the pre containing inline elements", async () => {
            await testEditor({
                contentBefore: "<pre><em>ab<strong>c[]</strong></em></pre>",
                stepFunction: splitBlock,
                contentAfter: "<pre><em>ab<strong>c</strong></em></pre><p>[]<br></p>",
            });
        });

        test("should be able to break out of an empty pre", async () => {
            await testEditor({
                contentBefore: "<pre>[]<br></pre>",
                stepFunction: splitBlock,
                contentAfter: "<pre><br></pre><p>[]<br></p>",
            });
        });
    });

    describe("Consecutive", () => {
        test("should duplicate an empty paragraph twice", async () => {
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                stepFunction: async (editor) => {
                    splitBlock(editor);
                    splitBlock(editor);
                },
                contentAfter: "<p><br></p><p><br></p><p>[]<br></p>",
            });
            // TODO this cannot actually be tested currently as a
            // backspace/delete in that case is not even detected
            // (no input event to rollback)
            // await testEditor({
            //     contentBefore: '<p>[<br>]</p>',
            //     stepFunction: async (editor) => {
            //         splitBlock(editor);
            //         splitBlock(editor);
            //     },
            //     contentAfter: '<p><br></p><p><br></p><p>[]<br></p>',
            // });
            await testEditor({
                contentBefore: "<p><br>[]</p>",
                stepFunction: async (editor) => {
                    splitBlock(editor);
                    splitBlock(editor);
                },
                contentAfter: "<p><br></p><p><br></p><p>[]<br></p>",
            });
        });

        test("should insert two empty paragraphs before a paragraph", async () => {
            await testEditor({
                contentBefore: "<p>[]abc</p>",
                stepFunction: async (editor) => {
                    splitBlock(editor);
                    splitBlock(editor);
                },
                contentAfter: "<p><br></p><p><br></p><p>[]abc</p>",
            });
        });

        test("should split a paragraph in three", async () => {
            await testEditor({
                contentBefore: "<p>ab[]cd</p>",
                stepFunction: async (editor) => {
                    splitBlock(editor);
                    splitBlock(editor);
                },
                contentAfter: "<p>ab</p><p><br></p><p>[]cd</p>",
            });
        });

        test("should split a paragraph in four", async () => {
            await testEditor({
                contentBefore: "<p>ab[]cd</p>",
                stepFunction: async (editor) => {
                    splitBlock(editor);
                    splitBlock(editor);
                    splitBlock(editor);
                },
                contentAfter: "<p>ab</p><p><br></p><p><br></p><p>[]cd</p>",
            });
        });

        test("should insert two empty paragraphs after a paragraph", async () => {
            await testEditor({
                contentBefore: "<p>abc[]</p>",
                stepFunction: async (editor) => {
                    splitBlock(editor);
                    splitBlock(editor);
                },
                contentAfter: "<p>abc</p><p><br></p><p>[]<br></p>",
            });
        });
    });

    describe("Format", () => {
        test("should split a paragraph before a format node", async () => {
            await testEditor({
                contentBefore: "<p>abc[]<b>def</b></p>",
                stepFunction: splitBlock,
                contentAfter: "<p>abc</p><p><b>[]def</b></p>",
            });
            await testEditor({
                // That selection is equivalent to []<b>
                contentBefore: "<p>abc<b>[]def</b></p>",
                stepFunction: splitBlock,
                contentAfter: "<p>abc</p><p><b>[]def</b></p>",
            });
            await testEditor({
                contentBefore: "<p>abc <b>[]def</b></p>",
                stepFunction: splitBlock,
                // The space is converted to a non-breaking
                // space so it is visible (because it's after a
                // <br>).
                contentAfter: "<p>abc&nbsp;</p><p><b>[]def</b></p>",
            });
            await testEditor({
                contentBefore: "<p>abc<b>[] def </b></p>",
                stepFunction: splitBlock,
                // The space is converted to a non-breaking
                // space so it is visible (because it's before a
                // <br>).
                // JW cAfter: '<p>abc</p><p><b>[]&nbsp;def</b></p>',
                contentAfter: "<p>abc</p><p><b>[]&nbsp;def </b></p>",
            });
        });

        test("should split a paragraph after a format node", async () => {
            await testEditor({
                contentBefore: "<p><b>abc</b>[]def</p>",
                stepFunction: splitBlock,
                contentAfter: "<p><b>abc</b></p><p>[]def</p>",
            });
            await testEditor({
                // That selection is equivalent to </b>[]
                contentBefore: "<p><b>abc[]</b>def</p>",
                stepFunction: splitBlock,
                contentAfter: "<p><b>abc</b></p><p>[]def</p>",
            });
            await testEditor({
                contentBefore: "<p><b>abc[]</b> def</p>",
                stepFunction: splitBlock,
                // The space is converted to a non-breaking
                // space so it is visible.
                contentAfter: "<p><b>abc</b></p><p>[]&nbsp;def</p>",
            });
            await testEditor({
                contentBefore: "<p><b>abc []</b>def</p>",
                stepFunction: splitBlock,
                // The space is converted to a non-breaking
                // space so it is visible (because it's before a
                // <br>).
                contentAfter: "<p><b>abc&nbsp;</b></p><p>[]def</p>",
            });
        });

        test("should split a paragraph at the beginning of a format node", async () => {
            await testEditor({
                contentBefore: "<p>[]<b>abc</b></p>",
                stepFunction: splitBlock,
                contentAfter: "<p><br></p><p><b>[]abc</b></p>",
            });
            await testEditor({
                // That selection is equivalent to []<b>
                contentBefore: "<p><b>[]abc</b></p>",
                stepFunction: splitBlock,
                contentAfter: "<p><br></p><p><b>[]abc</b></p>",
            });
            await testEditor({
                contentBefore: "<p><b>[] abc</b></p>",
                stepFunction: splitBlock,
                // The space should have been parsed away.
                // JW cAfter: '<p><br></p><p><b>[]abc</b></p>',
                contentAfter: "<p><br></p><p><b>[] abc</b></p>",
            });
        });

        test("should split a paragraph within a format node", async () => {
            await testEditor({
                contentBefore: "<p><b>ab[]cd</b></p>",
                stepFunction: splitBlock,
                contentAfter: "<p><b>ab</b></p><p><b>[]cd</b></p>",
            });
            await testEditor({
                contentBefore: "<p><b>ab []cd</b></p>",
                stepFunction: splitBlock,
                // The space is converted to a non-breaking
                // space so it is visible.
                contentAfter: "<p><b>ab&nbsp;</b></p><p><b>[]cd</b></p>",
            });
            await testEditor({
                contentBefore: "<p><b>ab[] cd</b></p>",
                stepFunction: splitBlock,
                // The space is converted to a non-breaking
                // space so it is visible.
                contentAfter: "<p><b>ab</b></p><p><b>[]&nbsp;cd</b></p>",
            });
        });

        test("should split a paragraph at the end of a format node", async () => {
            await testEditor({
                contentBefore: "<p><b>abc</b>[]</p>",
                stepFunction: splitBlock,
                contentAfter: "<p><b>abc</b></p><p>[]<br></p>",
            });
            await testEditor({
                // That selection is equivalent to </b>[]
                contentBefore: "<p><b>abc[]</b></p>",
                stepFunction: splitBlock,
                contentAfter: "<p><b>abc</b></p><p>[]<br></p>",
            });
            await testEditor({
                contentBefore: "<p><b>abc[] </b></p>",
                stepFunction: splitBlock,
                // The space should have been parsed away.
                contentAfter: "<p><b>abc</b></p><p>[]<br></p>",
            });
        });

        // skipping these tests cause with the link isolation the cursor can be put
        // inside/outside the link so the user can choose where to insert the line break
        // see `anchor.nodeName === "A" && brEls.includes(anchor.firstChild)` in line_break_plugin.js
        test.skip("should insert line breaks outside the edges of an anchor", async () => {
            const insertLinebreak = (editor) => {
                editor.dispatch("INSERT_LINEBREAK");
            };
            await testEditor({
                contentBefore: "<div>ab<a>[]cd</a></div>",
                stepFunction: insertLinebreak,
                contentAfter: "<div>ab<br><a>[]cd</a></div>",
            });
            await testEditor({
                contentBefore: "<div><a>a[]b</a></div>",
                stepFunction: insertLinebreak,
                contentAfter: "<div><a>a<br>[]b</a></div>",
            });
            await testEditor({
                contentBefore: "<div><a>ab[]</a></div>",
                stepFunction: insertLinebreak,
                contentAfter: "<div><a>ab</a><br>[]<br></div>",
            });
            await testEditor({
                contentBefore: "<div><a>ab[]</a>cd</div>",
                stepFunction: insertLinebreak,
                contentAfter: "<div><a>ab</a><br>[]cd</div>",
            });
        });
    });

    describe("With attributes", () => {
        test("should insert an empty paragraph before a paragraph with a span with a class", async () => {
            await testEditor({
                contentBefore: '<p><span class="a">ab</span></p><p><span class="b">[]cd</span></p>',
                stepFunction: splitBlock,
                contentAfter:
                    '<p><span class="a">ab</span></p><p><br></p><p><span class="b">[]cd</span></p>',
            });
        });

        test("should split a paragraph with a span with a bold in two", async () => {
            await testEditor({
                contentBefore: '<p><span class="a"><b>ab[]cd</b></span></p>',
                stepFunction: splitBlock,
                contentAfter:
                    '<p><span class="a"><b>ab</b></span></p><p><span class="a"><b>[]cd</b></span></p>',
            });
        });

        test("should split a paragraph at its end, with a paragraph after it, and both have the same class", async () => {
            await testEditor({
                contentBefore: '<p class="a">a[]</p><p class="a"><br></p>',
                stepFunction: splitBlock,
                contentAfter: '<p class="a">a</p><p class="a">[]<br></p><p class="a"><br></p>',
            });
        });
    });

    describe("POC extra tests", () => {
        test("should insert a paragraph after an empty h1", async () => {
            await testEditor({
                contentBefore: "<h1>[]<br></h1>",
                stepFunction: splitBlock,
                contentAfter: "<h1><br></h1><p>[]<br></p>",
            });
        });

        test("should insert a paragraph after an empty h1 with styles and a zero-width space", async () => {
            await testEditor({
                contentBefore:
                    '<h1><font style="color: red;" data-oe-zws-empty-inline="">[]\u200B</font><br></h1>',
                stepFunction: splitBlock,
                contentAfter: "<h1><br></h1><p>[]<br></p>",
            });
        });
    });
});

describe("Selection not collapsed", () => {
    test("should delete the first half of a paragraph, then split it", async () => {
        // Forward selection
        await testEditor({
            contentBefore: "<p>[ab]cd</p>",
            stepFunction: splitBlock,
            contentAfter: "<p><br></p><p>[]cd</p>",
        });
        // Backward selection
        await testEditor({
            contentBefore: "<p>]ab[cd</p>",
            stepFunction: splitBlock,
            contentAfter: "<p><br></p><p>[]cd</p>",
        });
    });

    test("should delete part of a paragraph, then split it", async () => {
        // Forward selection
        await testEditor({
            contentBefore: "<p>a[bc]d</p>",
            stepFunction: splitBlock,
            contentAfter: "<p>a</p><p>[]d</p>",
        });
        // Backward selection
        await testEditor({
            contentBefore: "<p>a]bc[d</p>",
            stepFunction: splitBlock,
            contentAfter: "<p>a</p><p>[]d</p>",
        });
    });

    test("should delete the last half of a paragraph, then split it", async () => {
        // Forward selection
        await testEditor({
            contentBefore: "<p>ab[cd]</p>",
            stepFunction: splitBlock,
            contentAfter: "<p>ab</p><p>[]<br></p>",
        });
        // Backward selection
        await testEditor({
            contentBefore: "<p>ab]cd[</p>",
            stepFunction: splitBlock,
            contentAfter: "<p>ab</p><p>[]<br></p>",
        });
    });

    test("should delete all contents of a paragraph, then split it", async () => {
        // Forward selection
        await testEditor({
            contentBefore: "<p>[abcd]</p>",
            stepFunction: splitBlock,
            contentAfter: "<p><br></p><p>[]<br></p>",
        });
        // Backward selection
        await testEditor({
            contentBefore: "<p>]abcd[</p>",
            stepFunction: splitBlock,
            contentAfter: "<p><br></p><p>[]<br></p>",
        });
    });
});
