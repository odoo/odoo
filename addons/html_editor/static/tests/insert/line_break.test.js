import { describe, test } from "@odoo/hoot";
import { testEditor } from "../_helpers/editor";
import { insertLineBreak } from "../_helpers/user_actions";

describe("Selection collapsed", () => {
    describe("Basic", () => {
        test("should insert a <br> into an empty paragraph", async () => {
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                stepFunction: insertLineBreak,
                contentAfter: "<p><br>[]<br></p>",
            });
            // TODO this cannot actually be tested currently as a
            // backspace/delete in that case is not even detected
            // (no input event to rollback)
            // await testEditor({
            //     contentBefore: '<p>[<br>]</p>',
            //     stepFunction: insertLineBreak,
            //     contentAfter: '<p><br>[]<br></p>',
            // });
            // TODO to check: the cursor cannot be in that position...
            // await testEditor({
            //     contentBefore: '<p><br>[]</p>',
            //     stepFunction: insertLineBreak,
            //     contentAfter: '<p><br>[]<br></p>',
            // });
        });

        test("should insert a <br> at the beggining of a paragraph (1)", async () => {
            await testEditor({
                contentBefore: "<p>[]abc</p>",
                stepFunction: insertLineBreak,
                contentAfter: "<p><br>[]abc</p>",
            });
        });

        test("should insert a <br> at the beggining of a paragraph (2)", async () => {
            await testEditor({
                contentBefore: "<p>[] abc</p>",
                stepFunction: insertLineBreak,
                // The space should have been parsed away.
                contentAfter: "<p><br>[]abc</p>",
            });
        });

        test("should insert a <br> within text (1)", async () => {
            await testEditor({
                contentBefore: "<p>ab[]cd</p>",
                stepFunction: insertLineBreak,
                contentAfter: "<p>ab<br>[]cd</p>",
            });
        });

        test("should insert a <br> within text (2)", async () => {
            await testEditor({
                contentBefore: "<p>ab []cd</p>",
                stepFunction: insertLineBreak,
                // The space is converted to a non-breaking space so it
                // is visible (because it's before a <br>).
                contentAfter: "<p>ab&nbsp;<br>[]cd</p>",
            });
        });

        test("should insert a <br> within text (3)", async () => {
            await testEditor({
                contentBefore: "<p>ab[] cd</p>",
                stepFunction: insertLineBreak,
                // The space is converted to a non-breaking space so it
                // is visible (because it's after a <br>).
                contentAfter: "<p>ab<br>[]&nbsp;cd</p>",
            });
        });

        test("should insert a line break (2 <br>) at the end of a paragraph", async () => {
            await testEditor({
                contentBefore: "<p>abc[]</p>",
                stepFunction: insertLineBreak,
                // The second <br> is needed to make the first
                // one visible.
                contentAfter: "<p>abc<br>[]<br></p>",
            });
        });
    });

    describe("Consecutive", () => {
        test("should insert two <br> at the beggining of an empty paragraph", async () => {
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                stepFunction: async (editor) => {
                    await insertLineBreak(editor);
                    await insertLineBreak(editor);
                },
                contentAfter: "<p><br><br>[]<br></p>",
            });
            // TODO this cannot actually be tested currently as a
            // backspace/delete in that case is not even detected
            // (no input event to rollback)
            // await testEditor({
            //     contentBefore: '<p>[<br>]</p>',
            //     stepFunction: async (editor) => {
            //         await insertLineBreak(editor);
            //         await insertLineBreak(editor);
            //     },
            //     contentAfter: '<p><br><br>[]<br></p>',
            // });
            // TODO seems like a theoretical case, if needed it could
            // be about checking at the start of the shift-enter if
            // we are not between left-state BR and right-state block.
            // await testEditor({
            //     contentBefore: '<p><br>[]</p>',
            //     stepFunction: async (editor) => {
            //         await insertLineBreak(editor);
            //         await insertLineBreak(editor);
            //     },
            //     contentAfter: '<p><br><br>[]<br></p>',
            // });
        });

        test("should insert two <br> at the beggining of a paragraph", async () => {
            await testEditor({
                contentBefore: "<p>[]abc</p>",
                stepFunction: async (editor) => {
                    await insertLineBreak(editor);
                    await insertLineBreak(editor);
                },
                contentAfter: "<p><br><br>[]abc</p>",
            });
        });

        test("should insert two <br> within text", async () => {
            await testEditor({
                contentBefore: "<p>ab[]cd</p>",
                stepFunction: async (editor) => {
                    await insertLineBreak(editor);
                    await insertLineBreak(editor);
                },
                contentAfter: "<p>ab<br><br>[]cd</p>",
            });
        });

        test("should insert two line breaks (3 <br>) at the end of a paragraph", async () => {
            await testEditor({
                contentBefore: "<p>abc[]</p>",
                stepFunction: async (editor) => {
                    await insertLineBreak(editor);
                    await insertLineBreak(editor);
                },
                // the last <br> is needed to make the first one
                // visible.
                contentAfter: "<p>abc<br><br>[]<br></p>",
            });
        });
        test("should insert two line breaks (2 <br>) before contenteditable false element", async () => {
            await testEditor({
                contentBefore: `<p>a[]<span contenteditable="false">b</span></p>`,
                stepFunction: async (editor) => {
                    await insertLineBreak(editor);
                    await insertLineBreak(editor);
                },
                contentAfter: `<p>a<br><br>[]<span contenteditable="false">b</span></p>`,
            });
        });
    });

    describe("Format", () => {
        test("should insert a <br> before a format node (1)", async () => {
            await testEditor({
                contentBefore: "<p>abc[]<b>def</b></p>",
                stepFunction: insertLineBreak,
                contentAfter: "<p>abc<br><b>[]def</b></p>",
            });
        });

        test("should insert a <br> before a format node (2)", async () => {
            await testEditor({
                // That selection is equivalent to []<b>
                contentBefore: "<p>abc<b>[]def</b></p>",
                stepFunction: insertLineBreak,
                // JW cAfter: '<p>abc<br><b>[]def</b></p>',
                contentAfter: "<p>abc<b><br>[]def</b></p>",
            });
        });

        test("should insert a <br> before a format node (3)", async () => {
            await testEditor({
                contentBefore: "<p>abc <b>[]def</b></p>",
                stepFunction: insertLineBreak,
                // The space is converted to a non-breaking space so it
                // is visible (because it's before a <br>).
                contentAfter: "<p>abc&nbsp;<b><br>[]def</b></p>",
            });
        });

        test("should insert a <br> before a format node (4)", async () => {
            await testEditor({
                contentBefore: "<p>abc<b>[] def </b></p>",
                stepFunction: insertLineBreak,
                // The space is converted to a non-breaking space so it
                // is visible (because it's before a <br>).
                contentAfter: "<p>abc<b><br>[]&nbsp;def </b></p>",
            });
        });

        test("should insert a <br> after a format node (1)", async () => {
            await testEditor({
                contentBefore: "<p><b>abc</b>[]def</p>",
                stepFunction: insertLineBreak,
                // JW cAfter: '<p><b>abc[]<br></b>def</p>',
                contentAfter: "<p><b>abc</b><br>[]def</p>",
            });
        });

        test("should insert a <br> after a format node (2)", async () => {
            await testEditor({
                // That selection is equivalent to </b>[]
                contentBefore: "<p><b>abc[]</b>def</p>",
                stepFunction: insertLineBreak,
                // JW cAfter: '<p><b>abc[]<br></b>def</p>',
                contentAfter: "<p><b>abc<br>[]</b>def</p>",
            });
        });

        test("should insert a <br> after a format node (3)", async () => {
            await testEditor({
                contentBefore: "<p><b>abc[]</b> def</p>",
                stepFunction: insertLineBreak,
                contentAfterEdit: "<p><b>abc<br>[]\ufeff</b> def</p>",
                // The space is converted to a non-breaking space so
                // it is visible (because it's after a <br>).
                // Visually, the caret does show _after_ the line
                // break.
                // JW cAfter: '<p><b>abc[]<br></b>&nbsp;def</p>',
                contentAfter: "<p><b>abc<br>[]</b>&nbsp;def</p>",
            });
        });

        test("should insert a <br> after a format node (4)", async () => {
            await testEditor({
                contentBefore: "<p><b>abc []</b>def</p>",
                stepFunction: insertLineBreak,
                // The space is converted to a non-breaking space so it
                // is visible (because it's before a <br>).
                contentAfter: "<p><b>abc&nbsp;<br>[]</b>def</p>",
            });
        });

        test("should insert a <br> at the beginning of a format node (1)", async () => {
            await testEditor({
                contentBefore: "<p>[]<b>abc</b></p>",
                stepFunction: insertLineBreak,
                contentAfter: "<p><b><br>[]abc</b></p>",
            });
        });

        test("should insert a <br> at the beginning of a format node (2)", async () => {
            await testEditor({
                // That selection is equivalent to []<b>
                contentBefore: "<p><b>[]abc</b></p>",
                stepFunction: insertLineBreak,
                contentAfter: "<p><b><br>[]abc</b></p>",
            });
        });

        test("should insert a <br> at the beginning of a format node (3)", async () => {
            await testEditor({
                contentBefore: "<p><b>[] abc</b></p>",
                stepFunction: insertLineBreak,
                // The space should have been parsed away.
                contentAfter: "<p><b><br>[]abc</b></p>",
            });
        });

        test("should insert a <br> within a format node (1)", async () => {
            await testEditor({
                contentBefore: "<p><b>ab[]cd</b></p>",
                stepFunction: insertLineBreak,
                contentAfter: "<p><b>ab<br>[]cd</b></p>",
            });
        });

        test("should insert a <br> within a format node (2)", async () => {
            await testEditor({
                contentBefore: "<p><b>ab []cd</b></p>",
                stepFunction: insertLineBreak,
                // The space is converted to a non-breaking space so it
                // is visible (because it's before a <br>).
                contentAfter: "<p><b>ab&nbsp;<br>[]cd</b></p>",
            });
        });

        test("should insert a <br> within a format node (3)", async () => {
            await testEditor({
                contentBefore: "<p><b>ab[] cd</b></p>",
                stepFunction: insertLineBreak,
                // The space is converted to a non-breaking
                // space so it is visible.
                contentAfter: "<p><b>ab<br>[]&nbsp;cd</b></p>",
            });
        });

        test("should insert \uFEFF at the end of format node", async () => {
            await testEditor({
                contentBefore: "<p><b>abc[]</b><br><br></p>",
                stepFunction: insertLineBreak,
                contentAfterEdit: `<p><b>abc<br>[]\uFEFF</b><br><br></p>`,
                contentAfter: "<p><b>abc<br>[]</b><br><br></p>",
            });
        });

        test("should insert a line break (2 <br>) at the end of a format node (1)", async () => {
            await testEditor({
                contentBefore: "<p><b>abc</b>[]</p>",
                stepFunction: insertLineBreak,
                // The second <br> is needed to make the first
                // one visible.
                contentAfter: "<p><b>abc<br>[]<br></b></p>",
            });
        });

        test("should insert a line break (2 <br>) at the end of a format node (2)", async () => {
            await testEditor({
                // That selection is equivalent to </b>[]
                contentBefore: "<p><b>abc[]</b></p>",
                stepFunction: insertLineBreak,
                // The second <br> is needed to make the first
                // one visible.
                contentAfter: "<p><b>abc<br>[]<br></b></p>",
            });
        });

        test("should insert a line break (2 <br>) at the end of a format node (3)", async () => {
            await testEditor({
                contentBefore: "<p><b>abc[] </b></p>",
                stepFunction: insertLineBreak,
                // The space should have been parsed away.
                // The second <br> is needed to make the first
                // one visible.
                contentAfter: "<p><b>abc<br>[]<br></b></p>",
            });
        });
    });

    describe("With attributes", () => {
        test("should insert a line break before a span with class", async () => {
            await testEditor({
                contentBefore:
                    '<p><span class="a">dom to</span></p><p><span class="b">[]edit</span></p>',
                stepFunction: insertLineBreak,
                contentAfter:
                    '<p><span class="a">dom to</span></p><p><span class="b"><br>[]edit</span></p>',
            });
        });

        test("should insert a line break within a span with a bold", async () => {
            await testEditor({
                contentBefore: '<p><span class="a"><b>ab[]cd</b></span></p>',
                stepFunction: insertLineBreak,
                contentAfter: '<p><span class="a"><b>ab<br>[]cd</b></span></p>',
            });
        });
    });
});

describe("Selection not collapsed", () => {
    test("should delete the first half of a paragraph, then insert a <br> (1)", async () => {
        // Forward selection
        await testEditor({
            contentBefore: "<p>[ab]cd</p>",
            stepFunction: insertLineBreak,
            contentAfter: "<p><br>[]cd</p>",
        });
    });

    test("should delete the first half of a paragraph, then insert a <br> (2)", async () => {
        // Backward selection
        await testEditor({
            contentBefore: "<p>]ab[cd</p>",
            stepFunction: insertLineBreak,
            contentAfter: "<p><br>[]cd</p>",
        });
    });

    test("should delete part of a paragraph, then insert a <br> (1)", async () => {
        // Forward selection
        await testEditor({
            contentBefore: "<p>a[bc]d</p>",
            stepFunction: insertLineBreak,
            contentAfter: "<p>a<br>[]d</p>",
        });
    });

    test("should delete part of a paragraph, then insert a <br> (2)", async () => {
        // Backward selection
        await testEditor({
            contentBefore: "<p>a]bc[d</p>",
            stepFunction: insertLineBreak,
            contentAfter: "<p>a<br>[]d</p>",
        });
    });

    test("should delete the last half of a paragraph, then insert a line break (2 <br>) (1)", async () => {
        // Forward selection
        await testEditor({
            contentBefore: "<p>ab[cd]</p>",
            stepFunction: insertLineBreak,
            // the second <br> is needed to make the first one
            // visible.
            contentAfter: "<p>ab<br>[]<br></p>",
        });
    });

    test("should delete the last half of a paragraph, then insert a line break (2 <br>) (2)", async () => {
        // Backward selection
        await testEditor({
            contentBefore: "<p>ab]cd[</p>",
            stepFunction: insertLineBreak,
            // the second <br> is needed to make the first one
            // visible.
            contentAfter: "<p>ab<br>[]<br></p>",
        });
    });

    test("should delete all contents of a paragraph, then insert a line break (1)", async () => {
        // Forward selection
        await testEditor({
            contentBefore: "<p>[abcd]</p>",
            stepFunction: insertLineBreak,
            contentAfter: "<p><br>[]<br></p>",
        });
    });

    test("should delete all contents of a paragraph, then insert a line break (2)", async () => {
        // Backward selection
        await testEditor({
            contentBefore: "<p>]abcd[</p>",
            stepFunction: insertLineBreak,
            contentAfter: "<p><br>[]<br></p>",
        });
    });
});

describe("table", () => {
    test("should remove all contents of an anchor td and insert a line break on forward selection", async () => {
        // Forward selection
        await testEditor({
            contentBefore: `
                <table>
                    <tbody>
                        <tr>
                            <td><p>[abc</p><p>def</p></td>
                            <td><p>abcd</p></td>
                            <td><p>ab]</p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>`,
            stepFunction: insertLineBreak,
            contentAfter: `
                <table>
                    <tbody>
                        <tr>
                            <td><p><br>[]<br></p></td>
                            <td><p>abcd</p></td>
                            <td><p>ab</p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>`,
        });
    });
    test("should remove all contents of an anchor td and insert a line break on backward selection", async () => {
        // Backward selection
        await testEditor({
            contentBefore: `
                <table>
                    <tbody>
                        <tr>
                            <td><p>]ab</p></td>
                            <td><p>abcd</p></td>
                            <td><p>abc</p><p>def[</p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>`,
            stepFunction: insertLineBreak,
            contentAfter: `
                <table>
                    <tbody>
                        <tr>
                            <td><p>ab</p></td>
                            <td><p>abcd</p></td>
                            <td><p><br>[]<br></p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>`,
        });
    });
});
