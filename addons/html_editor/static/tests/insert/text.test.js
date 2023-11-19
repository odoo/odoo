import { describe, test } from "@odoo/hoot";
import { testEditor } from "../_helpers/editor";
import { deleteBackward, insertText } from "../_helpers/user_actions";

describe("collapsed selection", () => {
    test("should insert a char into an empty span without removing the zws", async () => {
        await testEditor({
            contentBefore: '<p>ab<span class="a">[]\u200B</span>cd</p>',
            stepFunction: async (editor) => {
                insertText(editor, "x");
            },
            contentAfter: '<p>ab<span class="a">x[]\u200B</span>cd</p>',
        });
    });

    test("should insert a char into an empty span surrounded by space without removing the zws", async () => {
        await testEditor({
            contentBefore: '<p>ab <span class="a">[]\u200B</span> cd</p>',
            stepFunction: async (editor) => {
                insertText(editor, "x");
            },
            contentAfter: '<p>ab <span class="a">x[]\u200B</span> cd</p>',
        });
    });

    test("should insert a char into a data-oe-zws-empty-inline span removing the zws and data-oe-zws-empty-inline", async () => {
        await testEditor({
            contentBefore: '<p>ab<span data-oe-zws-empty-inline="">[]\u200B</span>cd</p>',
            stepFunction: async (editor) => {
                insertText(editor, "x");
            },
            contentAfter: "<p>ab<span>x[]</span>cd</p>",
        });
    });

    test("should insert a char into a data-oe-zws-empty-inline span surrounded by space without removing the zws and data-oe-zws-empty-inline", async () => {
        await testEditor({
            contentBefore: '<p>ab<span data-oe-zws-empty-inline="">[]\u200B</span>cd</p>',
            stepFunction: async (editor) => {
                insertText(editor, "x");
            },
            contentAfter: "<p>ab<span>x[]</span>cd</p>",
        });
    });
});

describe("not collapsed selection", () => {
    test("should insert a character in a fully selected font in a heading, preserving its style", async () => {
        await testEditor({
            contentBefore:
                '<h1><font style="background-color: red;">[abc</font><br></h1><p>]def</p>',
            stepFunction: async (editor) => insertText(editor, "g"),
            contentAfter: '<h1><font style="background-color: red;">g[]</font><br></h1><p>def</p>',
        });
        await testEditor({
            contentBefore:
                '<h1><font style="background-color: red;">[abc</font><br></h1><p>]def</p>',
            stepFunction: async (editor) => {
                deleteBackward(editor);
                insertText(editor, "g");
            },
            contentAfter: '<h1><font style="background-color: red;">g[]</font><br></h1><p>def</p>',
        });
    });

    test("should transform the space node preceded by a styled element to &nbsp;", async () => {
        await testEditor({
            contentBefore: `<p><strong>ab</strong> [cd]</p>`,
            stepFunction: async (editor) => {
                insertText(editor, "x");
            },
            contentAfter: `<p><strong>ab</strong>&nbsp;x[]</p>`,
        });
    });
});
