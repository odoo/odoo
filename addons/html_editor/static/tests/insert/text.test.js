import { describe, expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "../_helpers/editor";
import { deleteBackward, insertText } from "../_helpers/user_actions";
import { getContent } from "../_helpers/selection";
import { execCommand } from "../_helpers/userCommands";
import { press } from "@odoo/hoot-dom";
import { unformat } from "../_helpers/format";

describe("collapsed selection", () => {
    test("should insert a char into an empty span without removing the zws", async () => {
        await testEditor({
            contentBefore: '<p>ab<span class="a">[]\u200B</span>cd</p>',
            stepFunction: async (editor) => {
                await insertText(editor, "x");
            },
            contentAfter: '<p>ab<span class="a">x[]\u200B</span>cd</p>',
        });
    });

    test("should insert a char into an empty span surrounded by space without removing the zws", async () => {
        await testEditor({
            contentBefore: '<p>ab <span class="a">[]\u200B</span> cd</p>',
            stepFunction: async (editor) => {
                await insertText(editor, "x");
            },
            contentAfter: '<p>ab <span class="a">x[]\u200B</span> cd</p>',
        });
    });

    test("should insert a char into a data-oe-zws-empty-inline span removing the zws and data-oe-zws-empty-inline", async () => {
        await testEditor({
            contentBefore: '<p>ab<span data-oe-zws-empty-inline="">[]\u200B</span>cd</p>',
            stepFunction: async (editor) => {
                await insertText(editor, "x");
            },
            contentAfter: "<p>abx[]cd</p>",
        });
    });

    test("should insert a char into a data-oe-zws-empty-inline span surrounded by space without removing the zws and data-oe-zws-empty-inline", async () => {
        await testEditor({
            contentBefore: '<p>ab<span data-oe-zws-empty-inline="">[]\u200B</span>cd</p>',
            stepFunction: async (editor) => {
                await insertText(editor, "x");
            },
            contentAfter: "<p>abx[]cd</p>",
        });
    });

    test("should insert text within heading after selecting a heading using ctrl+A", async () => {
        await testEditor({
            contentBefore: "<h1>abc[]</h1><p>def</p>",
            stepFunction: async (editor) => {
                await press(["ctrl", "a"]);
                await insertText(editor, "x");
            },
            contentAfter: "<h1>x[]</h1>",
        });
    });
    test("should insert a char into an empty p and remove the br", async () => {
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: async (editor) => {
                await insertText(editor, "x");
            },
            contentAfter: "<p>x[]</p>",
        });
    });
    test("should insert a char into an p with br and remove the unecessary br", async () => {
        await testEditor({
            contentBefore: "<p>abc<br>[]<br></p>",
            stepFunction: async (editor) => {
                await insertText(editor, "x");
            },
            contentAfter: "<p>abc<br>x[]</p>",
        });
    });

    test("should insert text formatted empty node", async () => {
        await testEditor({
            contentBefore: unformat(`
                <div class="o-paragraph">
                    <strong data-oe-zws-empty-inline="">[]\ufeff</strong>
                </div>
            `),
            stepFunction: async (editor) => {
                await insertText(editor, "abc");
            },
            contentAfterEdit: unformat(`
                <div class="o-paragraph">
                    <strong>abc[]</strong>
                </div>
            `),
        });
    });
});

describe("not collapsed selection", () => {
    test("should insert a character in a fully selected font in a heading, preserving its style", async () => {
        await testEditor({
            contentBefore:
                '<h1><font style="background-color: red;">[abc]</font><br></h1><p>def</p>',
            stepFunction: async (editor) => await insertText(editor, "g"),
            contentAfter: '<h1><font style="background-color: red;">g[]</font><br></h1><p>def</p>',
        });
        await testEditor({
            contentBefore:
                '<h1><font style="background-color: red;">[abc]</font><br></h1><p>def</p>',
            stepFunction: async (editor) => {
                deleteBackward(editor);
                await insertText(editor, "g");
            },
            contentAfter: '<h1><font style="background-color: red;">g[]</font><br></h1><p>def</p>',
        });
    });

    test("should transform the space node preceded by a styled element to &nbsp;", async () => {
        await testEditor({
            contentBefore: `<p><strong>ab</strong> [cd]</p>`,
            stepFunction: async (editor) => {
                await insertText(editor, "x");
            },
            contentAfter: `<p><strong>ab</strong>&nbsp;x[]</p>`,
        });
    });

    test("should replace text and be a undoable step", async () => {
        const { editor, el } = await setupEditor("<p>[abc]def</p>");
        await insertText(editor, "x");
        expect(getContent(el)).toBe("<p>x[]def</p>");
        execCommand(editor, "historyUndo");
        expect(getContent(el)).toBe("<p>[abc]def</p>");
    });
});
