import { describe, expect, test } from "@odoo/hoot";
import { press, queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { setupEditor, testEditor } from "./_helpers/editor";
import { getContent, setSelection } from "./_helpers/selection";
import { insertText, redo, undo } from "./_helpers/user_actions";
import { execCommand } from "./_helpers/userCommands";
import { nodeSize } from "@html_editor/utils/position";

function columnsContainer(contents) {
    return `<div class="container o_text_columns o-contenteditable-false"><div class="row">${contents}</div></div>`;
}

function column(size, contents) {
    return `<div class="col-${size} o-contenteditable-true">${contents}</div>`;
}

function columsDuringEditContainer(contents) {
    return `<div class="container o_text_columns o-contenteditable-false" contenteditable="false"><div class="row">${contents}</div></div>`;
}

function columnDuringEdit(size, contents) {
    return `<div class="col-${size} o-contenteditable-true" contenteditable="true">${contents}</div>`;
}

function columnize(numberOfColumns) {
    return (editor) => {
        execCommand(editor, "columnize", { numberOfColumns });
    };
}

describe("2 columns", () => {
    test("should display hint for focused empty column.", async () => {
        await testEditor({
            /* eslint-disable */
            contentBefore:
                columnsContainer(
                    column(6, "<p>[]<br></p>") +
                    column(6, "<p><br></p>")
                ),
            contentAfterEdit:
                columsDuringEditContainer(
                    columnDuringEdit(6, `<p placeholder="Empty column" class="o-we-hint">[]<br></p>`) +
                    columnDuringEdit(6, `<p><br></p>`)
                ),
            /* eslint-enable */
        });
    });

    test("should display the normal hint when cursor is in an empty cell of an empty table in one of the columns", async () => {
        await testEditor({
            /* eslint-disable */
            contentBefore:
                columnsContainer(
                    column(6, `<table><tbody><tr><td><p>[]<br></p></td><td><p><br></p></td></tr></tbody></table>`) +
                    column(6, "<p><br></p>")
                ),
            contentAfterEdit:
                columsDuringEditContainer(
                    columnDuringEdit(6, `<table><tbody><tr><td><p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p></td><td><p><br></p></td></tr></tbody></table>`) +
                    columnDuringEdit(6, `<p><br></p>`)
                ),
            /* eslint-enable */
        });
    });

    test("should do nothing", async () => {
        await testEditor({
            contentBefore: columnsContainer(
                column(6, "<p>abcd</p>") + column(6, "<h1>[]ef</h1><ul><li>gh</li></ul>")
            ),
            stepFunction: columnize(2),
            contentAfter: columnsContainer(
                column(6, "<p>abcd</p>") + column(6, "<h1>[]ef</h1><ul><li>gh</li></ul>")
            ),
        });
    });

    test("should turn text into 2 columns", async () => {
        await testEditor({
            contentBefore: "<p>[]abcd</p>",
            stepFunction: columnize(2),
            contentAfterEdit:
            /* eslint-disable */
                columsDuringEditContainer(
                    columnDuringEdit(6, "<p>[]abcd</p>") +
                    columnDuringEdit(6, `<p><br></p>`)
                ) +
                "<p><br></p>",
            contentAfter:
                columnsContainer(
                    column(6, "<p>[]abcd</p>") +
                    column(6, "<p><br></p>")
                ) +
                "<p><br></p>",
            /* eslint-enable */
        });
    });

    test("should turn 3 columns into 2 columns", async () => {
        await testEditor({
            contentBefore: columnsContainer(
                column(4, "<p>abcd</p>") +
                    column(4, "<h1>e[]f</h1>") +
                    column(4, "<ul><li>gh</li></ul>")
            ),
            stepFunction: columnize(2),
            contentAfter: columnsContainer(
                column(6, "<p>abcd</p>") + column(6, "<h1>e[]f</h1><ul><li>gh</li></ul>")
            ),
        });
    });

    test("should turn 4 columns into 2 columns", async () => {
        await testEditor({
            contentBefore: columnsContainer(
                column(3, "<p>abcd</p>") +
                    column(3, "<h1>ef</h1>") +
                    column(3, "<ul><li>gh</li></ul>") +
                    column(3, "<p>i[]j</p>")
            ),
            stepFunction: columnize(2),
            contentAfter: columnsContainer(
                column(6, "<p>abcd</p>") + column(6, "<h1>ef</h1><ul><li>gh</li></ul><p>i[]j</p>")
            ),
        });
    });

    test("apply '2 columns' powerbox command", async () => {
        const { el, editor } = await setupEditor("<p>ab[]cd</p>");
        await insertText(editor, "/2columns");
        await animationFrame();
        expect(".active .o-we-command-name").toHaveText("2 columns");

        await press("enter");
        expect(getContent(el)).toBe(
            `<div class="container o_text_columns o-contenteditable-false" contenteditable="false"><div class="row"><div class="col-6 o-contenteditable-true" contenteditable="true"><p>ab[]cd</p></div><div class="col-6 o-contenteditable-true" contenteditable="true"><p><br></p></div></div></div><p><br></p>`
        );

        await insertText(editor, "/columns");
        await animationFrame();
        expect(queryAllTexts(".o-we-command-name")).toEqual([
            "3 columns",
            "4 columns",
            "Remove columns",
        ]);
    });
});
describe("3 columns", () => {
    test("should do nothing", async () => {
        await testEditor({
            contentBefore: columnsContainer(
                column(4, "<p>abcd</p>") + column(4, "<p><br></p>") + column(4, "<p>[]<br></p>")
            ),
            /* eslint-disable */
            contentBeforeEdit:
                columsDuringEditContainer(
                    columnDuringEdit(4, "<p>abcd</p>") +
                    columnDuringEdit(4, `<p><br></p>`) +
                    columnDuringEdit(4, `<p placeholder="Empty column" class="o-we-hint">[]<br></p>`)
                ),
            /* eslint-enable */
            stepFunction: columnize(3),
            contentAfter: columnsContainer(
                column(4, "<p>abcd</p>") + column(4, "<p><br></p>") + column(4, "<p>[]<br></p>")
            ),
        });
    });

    test("should turn text into 3 columns", async () => {
        await testEditor({
            contentBefore: "<p>ab[]cd</p>",
            stepFunction: columnize(3),
            /* eslint-disable */
            contentAfterEdit:
                columsDuringEditContainer(
                    columnDuringEdit(4, "<p>ab[]cd</p>") +
                    columnDuringEdit(4, `<p><br></p>`) +
                    columnDuringEdit(4, `<p><br></p>`)
                ) + "<p><br></p>",
            contentAfter:
                columnsContainer(
                    column(4, "<p>ab[]cd</p>") +
                    column(4, "<p><br></p>") +
                    column(4, "<p><br></p>")
                ) + "<p><br></p>",
            /* eslint-enable */
        });
    });

    test("should turn 2 columns into 3 columns", async () => {
        await testEditor({
            contentBefore: columnsContainer(
                column(6, "<p>abcd</p>") + column(6, "<h1>ef</h1><ul><li>g[]h</li></ul>")
            ),
            stepFunction: columnize(3),
            contentAfter: columnsContainer(
                column(4, "<p>abcd</p>") +
                    column(4, "<h1>ef</h1><ul><li>g[]h</li></ul>") +
                    column(4, "<p><br></p>")
            ),
        });
    });

    test("should turn 4 columns into 3 columns", async () => {
        await testEditor({
            contentBefore: columnsContainer(
                column(3, "<p>abcd</p>") +
                    column(3, "<h1>e[]f</h1>") +
                    column(3, "<ul><li>gh</li></ul>") +
                    column(3, "<p>ij</p>")
            ),
            stepFunction: columnize(3),
            contentAfter: columnsContainer(
                column(4, "<p>abcd</p>") +
                    column(4, "<h1>e[]f</h1>") +
                    column(4, "<ul><li>gh</li></ul><p>ij</p>")
            ),
        });
    });

    test("apply '3 columns' powerbox command", async () => {
        const { el, editor } = await setupEditor("<p>ab[]cd</p>");
        await insertText(editor, "/3columns");
        await animationFrame();
        expect(".active .o-we-command-name").toHaveText("3 columns");

        await press("enter");
        expect(getContent(el)).toBe(
            `<div class="container o_text_columns o-contenteditable-false" contenteditable="false"><div class="row"><div class="col-4 o-contenteditable-true" contenteditable="true"><p>ab[]cd</p></div><div class="col-4 o-contenteditable-true" contenteditable="true"><p><br></p></div><div class="col-4 o-contenteditable-true" contenteditable="true"><p><br></p></div></div></div><p><br></p>`
        );

        await insertText(editor, "/columns");
        await animationFrame();
        expect(queryAllTexts(".o-we-command-name")).toEqual([
            "2 columns",
            "4 columns",
            "Remove columns",
        ]);
    });
});

describe("4 columns", () => {
    test("should do nothing", async () => {
        await testEditor({
            contentBefore: columnsContainer(
                column(3, "<p>abcd</p>") +
                    column(3, "<p><br></p>") +
                    column(3, "<p><br></p>") +
                    column(3, "<p>[]<br></p>")
            ),
            stepFunction: columnize(4),
            contentAfter: columnsContainer(
                column(3, "<p>abcd</p>") +
                    column(3, "<p><br></p>") +
                    column(3, "<p><br></p>") +
                    column(3, "<p>[]<br></p>")
            ),
        });
    });

    test("should turn text into 4 columns", async () => {
        await testEditor({
            contentBefore: "<p>abcd[]</p>",
            stepFunction: columnize(4),
            contentAfter:
                columnsContainer(
                    column(3, "<p>abcd[]</p>") +
                        column(3, "<p><br></p>") +
                        column(3, "<p><br></p>") +
                        column(3, "<p><br></p>")
                ) + "<p><br></p>",
        });
    });

    test("should turn 2 columns into 4 columns", async () => {
        await testEditor({
            contentBefore: columnsContainer(
                column(6, "<p>abcd</p>") + column(6, "<h1>[]ef</h1><ul><li>gh</li></ul>")
            ),
            stepFunction: columnize(4),
            contentAfter: columnsContainer(
                column(3, "<p>abcd</p>") +
                    column(3, "<h1>[]ef</h1><ul><li>gh</li></ul>") +
                    column(3, "<p><br></p>") +
                    column(3, "<p><br></p>")
            ),
        });
    });

    test("should turn 3 columns into 4 columns", async () => {
        await testEditor({
            contentBefore: columnsContainer(
                column(4, "<p>abcd</p>") +
                    column(4, "<h1>ef[]</h1>") +
                    column(4, "<ul><li>gh</li></ul><p>ij</p>")
            ),
            stepFunction: columnize(4),
            contentAfter: columnsContainer(
                column(3, "<p>abcd</p>") +
                    column(3, "<h1>ef[]</h1>") +
                    column(3, "<ul><li>gh</li></ul><p>ij</p>") +
                    column(3, "<p><br></p>")
            ),
        });
    });

    test("apply '4 columns' powerbox command", async () => {
        const { el, editor } = await setupEditor("<p>ab[]cd</p>");
        await insertText(editor, "/4columns");
        await animationFrame();
        expect(".active .o-we-command-name").toHaveText("4 columns");

        await press("enter");
        expect(getContent(el)).toBe(
            `<div class="container o_text_columns o-contenteditable-false" contenteditable="false"><div class="row"><div class="col-3 o-contenteditable-true" contenteditable="true"><p>ab[]cd</p></div><div class="col-3 o-contenteditable-true" contenteditable="true"><p><br></p></div><div class="col-3 o-contenteditable-true" contenteditable="true"><p><br></p></div><div class="col-3 o-contenteditable-true" contenteditable="true"><p><br></p></div></div></div><p><br></p>`
        );

        await insertText(editor, "/columns");
        await animationFrame();
        expect(queryAllTexts(".o-we-command-name")).toEqual([
            "2 columns",
            "3 columns",
            "Remove columns",
        ]);
    });
});

describe("remove columns", () => {
    test("should do nothing", async () => {
        await testEditor({
            contentBefore: "<p>ab[]cd</p>",
            stepFunction: columnize(0),
            contentAfter: "<p>ab[]cd</p>",
        });
    });

    test("should turn 2 columns into text", async () => {
        await testEditor({
            contentBefore: columnsContainer(
                column(6, "<p>abcd</p>") + column(6, "<h1>[]ef</h1><ul><li>gh</li></ul>")
            ),
            stepFunction: columnize(0),
            contentAfter: "<p>abcd</p><h1>[]ef</h1><ul><li>gh</li></ul>",
        });
    });

    test("should turn 3 columns into text", async () => {
        await testEditor({
            contentBefore: columnsContainer(
                column(4, "<p>abcd</p>") +
                    column(4, "<h1>ef[]</h1>") +
                    column(4, "<ul><li>gh</li></ul><p>ij</p>")
            ),
            stepFunction: columnize(0),
            contentAfter: "<p>abcd</p><h1>ef[]</h1><ul><li>gh</li></ul><p>ij</p>",
        });
    });

    test("should turn 4 columns into text", async () => {
        await testEditor({
            contentBefore: columnsContainer(
                column(3, "<p>abcd</p>") +
                    column(3, "<h1>ef</h1>") +
                    column(3, "<ul><li>gh</li></ul><p>ij</p>") +
                    column(3, "<p>[]<br></p>")
            ),
            stepFunction: columnize(0),
            contentAfter: "<p>abcd</p><h1>ef</h1><ul><li>gh</li></ul><p>ij</p><p>[]<br></p>",
        });
    });

    test("apply 'remove columns' powerbox command", async () => {
        const { el, editor } = await setupEditor("<p>ab[]cd</p>");
        await insertText(editor, "/columns");
        await animationFrame();
        expect(queryAllTexts(".o-we-command-name")).toEqual([
            "2 columns",
            "3 columns",
            "4 columns",
        ]);

        // add 2 columns
        await press("enter");
        expect(getContent(el)).toBe(
            `<div class="container o_text_columns o-contenteditable-false" contenteditable="false"><div class="row"><div class="col-6 o-contenteditable-true" contenteditable="true"><p>ab[]cd</p></div><div class="col-6 o-contenteditable-true" contenteditable="true"><p><br></p></div></div></div><p><br></p>`
        );

        await insertText(editor, "/removecolumns");
        await animationFrame();
        expect(".active .o-we-command-name").toHaveText("Remove columns");
        await press("enter");
        expect(getContent(el)).toBe(`<p>ab[]cd</p><p><br></p><p><br></p>`);
    });
});

describe("complex", () => {
    test("should turn text into 2 columns, then 3, 4, 3, 2 and text again", async () => {
        await testEditor({
            contentBefore: "<p>ab[]cd</p>",
            stepFunction: (editor) => {
                columnize(2)(editor);
                columnize(3)(editor);
                columnize(4)(editor);
                columnize(3)(editor);
                columnize(2)(editor);
                columnize(0)(editor);
            },
            // A paragraph was created for each column + after them and
            // they were all kept.
            contentAfter: "<p>ab[]cd</p><p><br></p><p><br></p><p><br></p><p><br></p>",
        });
    });

    test("should not add a container when one already exists", async () => {
        await testEditor({
            contentBefore:
                '<div class="container o-contenteditable-false"><div class="row"><div class="col o-contenteditable-true">' +
                "<p>ab[]cd</p>" +
                "</div></div></div>",
            stepFunction: columnize(2),
            contentAfter:
                '<div class="container o-contenteditable-false"><div class="row"><div class="col o-contenteditable-true">' +
                '<div class="o_text_columns o-contenteditable-false"><div class="row">' + // no "container" class
                '<div class="col-6 o-contenteditable-true">' +
                "<p>ab[]cd</p>" +
                "</div>" +
                '<div class="col-6 o-contenteditable-true"><p><br></p></div>' +
                "</div></div>" +
                "<p><br></p>" +
                "</div></div></div>",
        });
    });
});

describe("undo", () => {
    test("should be able to write after undo", async () => {
        await testEditor({
            contentBefore: "<p>[]</p>",
            stepFunction: async (editor) => {
                columnize(2)(editor);
                undo(editor);
                await insertText(editor, "x");
            },
            contentAfter: "<p>x[]</p>",
        });
    });

    test("should work properly after undo and then redo", async () => {
        await testEditor({
            contentBefore: "<p>[]</p>",
            stepFunction: async (editor) => {
                columnize(2)(editor);
                undo(editor);
                redo(editor);
                await insertText(editor, "x");
            },
            contentAfter:
                columnsContainer(column(6, "<p>x[]</p>") + column(6, "<p><br></p>")) +
                "<p><br></p>",
        });
    });
});

describe("selection", () => {
    test("should be able to select across columns using Shift + ArrowUp", async () => {
        await testEditor({
            contentBefore: "<p>a</p><p>b[]</p>",
            stepFunction: async (editor) => {
                columnize(2)(editor);
                const editable = editor.editable;
                const children = editable.querySelectorAll("p");
                const lastP = children[children.length - 1];
                lastP.innerHTML = "ab";
                setSelection({ anchorNode: lastP.firstChild, anchorOffset: 0 });
                await press(["shift", "arrowUp"]);
            },
            contentAfter:
                "<p>a]</p>" +
                columnsContainer(column(6, "<p>b</p>") + column(6, "<p><br></p>")) +
                "<p>[ab</p>",
        });
    });
    test("should be able to select across columns using Shift + ArrowDown", async () => {
        await testEditor({
            contentBefore: "<p>a</p><p>b[]</p>",
            stepFunction: async (editor) => {
                columnize(2)(editor);
                const editable = editor.editable;
                const children = editable.querySelectorAll("p");
                const lastP = children[children.length - 1];
                lastP.innerHTML = "ab";
                const firstP = children[0];
                setSelection({ anchorNode: firstP.lastChild, anchorOffset: nodeSize(firstP) });
                await press(["shift", "arrowDown"]);
            },
            contentAfter:
                "<p>a[</p>" +
                columnsContainer(column(6, "<p>b</p>") + column(6, "<p><br></p>")) +
                "<p>]ab</p>",
        });
    });
});
