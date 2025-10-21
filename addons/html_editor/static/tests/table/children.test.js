import { findInSelection } from "@html_editor/utils/selection";
import { describe, expect, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { setupEditor, testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { undo } from "../_helpers/user_actions";
import { getContent } from "../_helpers/selection";

function addRow(position) {
    return (editor) => {
        const selection = editor.shared.selection.getEditableSelection();
        editor.shared.table.addRow(position, findInSelection(selection, "tr"));
    };
}

function addColumn(position) {
    return (editor) => {
        const selection = editor.shared.selection.getEditableSelection();
        editor.shared.table.addColumn(position, findInSelection(selection, "td, th"));
    };
}

function turnIntoHeader(row) {
    return (editor) => {
        if (!row) {
            const selection = editor.shared.selection.getEditableSelection();
            row = findInSelection(selection, "tr");
        }
        editor.shared.table.turnIntoHeader(row);
    };
}

function turnIntoRow(row) {
    return (editor) => {
        if (!row) {
            const selection = editor.shared.selection.getEditableSelection();
            row = findInSelection(selection, "tr");
        }
        editor.shared.table.turnIntoRow(row);
    };
}

function moveRow(position, row) {
    return (editor) => {
        if (!row) {
            const selection = editor.shared.selection.getEditableSelection();
            row = findInSelection(selection, "tr");
        }
        editor.shared.table.moveRow(position, row);
    };
}

function removeRow(row) {
    return (editor) => {
        if (!row) {
            const selection = editor.shared.selection.getEditableSelection();
            row = findInSelection(selection, "tr");
        }
        editor.shared.table.removeRow(row);
    };
}

function removeColumn(cell) {
    return (editor) => {
        if (!cell) {
            const selection = editor.shared.selection.getEditableSelection();
            cell = findInSelection(selection, "td");
        }
        editor.shared.table.removeColumn(cell);
    };
}

describe("row", () => {
    describe("convert", () => {
        test("should convert the first row to table header", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <table>
                        <tbody>
                            <tr style="height: 20px;">
                                <td style="width: 20px;">ab[]</td>
                                <td style="width: 25px;">cd</td>
                                <td style="width: 30px;">ef</td>
                            </tr>
                            <tr style="height: 30px;">
                                <td>ab</td>
                                <td>cd</td>
                                <td>ef</td>
                            </tr>
                        </tbody>
                    </table>
                `),
                stepFunction: turnIntoHeader(),
                contentAfter: unformat(`
                    <table>
                        <tbody>
                            <tr style="height: 20px;">
                                <th class="o_table_header" style="width: 20px;">ab[]</th>
                                <th class="o_table_header" style="width: 25px;">cd</th>
                                <th class="o_table_header" style="width: 30px;">ef</th>
                            </tr>
                            <tr style="height: 30px;">
                                <td>ab</td>
                                <td>cd</td>
                                <td>ef</td>
                            </tr>
                        </tbody>
                    </table>
                `),
            });
        });

        test("should convert table header to normal row", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <table>
                        <tbody>
                            <tr style="height: 20px;">
                                <td style="width: 20px;">ab[]</td>
                                <td style="width: 25px;">cd</td>
                                <td style="width: 30px;">ef</td>
                            </tr>
                            <tr style="height: 30px;">
                                <td>ab</td>
                                <td>cd</td>
                                <td>ef</td>
                            </tr>
                        </tbody>
                    </table>
                `),
                stepFunction: turnIntoRow(),
                contentAfter: unformat(`
                    <table>
                        <tbody>
                            <tr style="height: 20px;">
                                <td style="width: 20px;">ab[]</td>
                                <td style="width: 25px;">cd</td>
                                <td style="width: 30px;">ef</td>
                            </tr>
                            <tr style="height: 30px;">
                                <td>ab</td>
                                <td>cd</td>
                                <td>ef</td>
                            </tr>
                        </tbody>
                    </table>
                `),
            });
        });
    });

    describe("above", () => {
        test("should add a row above the top row", async () => {
            await testEditor({
                contentBefore:
                    '<table><tbody><tr style="height: 20px;">' +
                    '<td style="width: 20px;">ab</td>' +
                    '<td style="width: 25px;">cd</td>' +
                    '<td style="width: 30px;">ef[]</td>' +
                    "</tr></tbody></table>",
                stepFunction: addRow("before"),
                contentAfter:
                    '<table><tbody><tr style="height: 20px;">' +
                    '<td style="width: 20px;"><p><br></p></td>' +
                    '<td style="width: 25px;"><p><br></p></td>' +
                    '<td style="width: 30px;"><p><br></p></td>' +
                    "</tr>" +
                    '<tr style="height: 20px;">' +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef[]</td>" +
                    "</tr></tbody></table>",
            });
        });

        test("should add a row above the middle row", async () => {
            await testEditor({
                contentBefore:
                    '<table><tbody><tr style="height: 20px;">' +
                    '<td style="width: 20px;">ab</td>' +
                    '<td style="width: 25px;">cd</td>' +
                    '<td style="width: 30px;">ef</td>' +
                    "</tr>" +
                    '<tr style="height: 30px;">' +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef[]</td>" +
                    "</tr></tbody></table>",
                stepFunction: addRow("before"),
                contentAfter:
                    '<table><tbody><tr style="height: 20px;">' +
                    '<td style="width: 20px;">ab</td>' +
                    '<td style="width: 25px;">cd</td>' +
                    '<td style="width: 30px;">ef</td>' +
                    "</tr>" +
                    '<tr style="height: 30px;">' +
                    "<td><p><br></p></td>" +
                    "<td><p><br></p></td>" +
                    "<td><p><br></p></td>" +
                    "</tr>" +
                    '<tr style="height: 30px;">' +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef[]</td>" +
                    "</tr></tbody></table>",
            });
        });
    });

    describe("below", () => {
        test("should add a row below the bottom row", async () => {
            await testEditor({
                contentBefore:
                    '<table><tbody><tr style="height: 20px;">' +
                    '<td style="width: 20px;">ab</td>' +
                    '<td style="width: 25px;">cd</td>' +
                    '<td style="width: 30px;">ef[]</td>' +
                    "</tr></tbody></table>",
                stepFunction: addRow("after"),
                contentAfter:
                    '<table><tbody><tr style="height: 20px;">' +
                    '<td style="width: 20px;">ab</td>' +
                    '<td style="width: 25px;">cd</td>' +
                    '<td style="width: 30px;">ef[]</td>' +
                    "</tr>" +
                    '<tr style="height: 20px;">' +
                    "<td><p><br></p></td>" +
                    "<td><p><br></p></td>" +
                    "<td><p><br></p></td>" +
                    "</tr></tbody></table>",
            });
        });

        test("should add a row below the middle row", async () => {
            await testEditor({
                contentBefore:
                    '<table><tbody><tr style="height: 20px;">' +
                    '<td style="width: 20px;">ab</td>' +
                    '<td style="width: 25px;">cd</td>' +
                    '<td style="width: 30px;">ef[]</td>' +
                    "</tr>" +
                    '<tr style="height: 30px;">' +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr></tbody></table>",
                stepFunction: addRow("after"),
                contentAfter:
                    '<table><tbody><tr style="height: 20px;">' +
                    '<td style="width: 20px;">ab</td>' +
                    '<td style="width: 25px;">cd</td>' +
                    '<td style="width: 30px;">ef[]</td>' +
                    "</tr>" +
                    '<tr style="height: 20px;">' +
                    "<td><p><br></p></td>" +
                    "<td><p><br></p></td>" +
                    "<td><p><br></p></td>" +
                    "</tr>" +
                    '<tr style="height: 30px;">' +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr></tbody></table>",
            });
        });
    });

    describe("move", () => {
        test("should move header row down and convert it to normal row", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <table>
                        <tbody>
                            <tr style="height: 20px;">
                                <th class="o_table_header" style="width: 20px;">ab[]</th>
                                <th class="o_table_header" style="width: 25px;">cd</th>
                                <th class="o_table_header" style="width: 30px;">ef</th>
                            </tr>
                            <tr style="height: 30px;">
                                <td>gh</td>
                                <td>ij</td>
                                <td>kl</td>
                            </tr>
                        </tbody>
                    </table>
                `),
                stepFunction: moveRow("down"),
                contentAfter: unformat(`
                    <table>
                        <tbody>
                            <tr style="height: 30px;">
                                <th class="o_table_header" style="width: 20px;">gh</th>
                                <th class="o_table_header" style="width: 25px;">ij</th>
                                <th class="o_table_header" style="width: 30px;">kl</th>
                            </tr>
                            <tr style="height: 20px;">
                                <td style="width: 20px;">ab[]</td>
                                <td style="width: 25px;">cd</td>
                                <td style="width: 30px;">ef</td>
                            </tr>
                        </tbody>
                    </table>
                `),
            });
        });

        test("should move second row up and convert it to header row", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <table>
                        <tbody>
                            <tr style="height: 20px;">
                                <th class="o_table_header" style="width: 20px;">ab</th>
                                <th class="o_table_header" style="width: 25px;">cd</th>
                                <th class="o_table_header" style="width: 30px;">ef</th>
                            </tr>
                            <tr style="height: 30px;">
                                <td>gh</td>
                                <td>ij</td>
                                <td>kl[]</td>
                            </tr>
                        </tbody>
                    </table>
                `),
                stepFunction: moveRow("up"),
                contentAfter: unformat(`
                    <table>
                        <tbody>
                            <tr style="height: 30px;">
                                <th class="o_table_header" style="width: 20px;">gh</th>
                                <th class="o_table_header" style="width: 25px;">ij</th>
                                <th class="o_table_header" style="width: 30px;">kl[]</th>
                            </tr>
                            <tr style="height: 20px;">
                                <td style="width: 20px;">ab</td>
                                <td style="width: 25px;">cd</td>
                                <td style="width: 30px;">ef</td>
                            </tr>
                        </tbody>
                    </table>
                `),
            });
        });
    });

    describe("removal", () => {
        test("should remove a row based on selection", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td>[]ab</td> <td>cd</td>
                            </tr>
                            <tr>
                                <td>ef</td> <td>gh</td>
                            </tr>
                        </tbody>
                    </table>
                `),
                stepFunction: removeRow(),
                // @todo @phoenix: consider changing the behavior and placing the cursor
                // inside the td (normalize deep)
                contentAfter: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td>[]ef</td> <td>gh</td>
                            </tr>
                        </tbody>
                    </table>
                `),
            });
        });
        test("should remove the row passed as argument", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td>[]ab</td> <td>cd</td>
                            </tr>
                            <tr>
                                <td>ef</td> <td>gh</td>
                            </tr>
                        </tbody>
                    </table>
                `),
                stepFunction: (editor) => {
                    // Select the second row
                    const row = editor.editable.querySelectorAll("tr")[1];
                    removeRow(row)(editor);
                },
                contentAfter: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td>[]ab</td> <td>cd</td>
                            </tr>
                        </tbody>
                    </table>
                `),
            });
        });
        test("should remove the table upon sole row removal", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td>[]ab</td> <td>cd</td>
                            </tr>
                        </tbody>
                    </table>
                `),
                contentBeforeEdit: unformat(
                    `<p data-selection-placeholder=""><br></p>
                    <table>
                        <tbody>
                            <tr>
                                <td>[]ab</td> <td>cd</td>
                            </tr>
                        </tbody>
                    </table>
                    <p data-selection-placeholder=""><br></p>`
                ),
                stepFunction: removeRow(),
                contentAfter: "<p>[]<br></p>",
            });
        });
    });
});

describe("column", () => {
    describe("left", () => {
        test("should add a column left of the leftmost column", async () => {
            await testEditor({
                contentBefore:
                    '<table style="width: 150px;"><tbody><tr style="height: 20px;">' +
                    '<td style="width: 40px;">ab[]</td>' +
                    '<td style="width: 50px;">cd</td>' +
                    '<td style="width: 60px;">ef</td>' +
                    "</tr>" +
                    '<tr style="height: 30px;">' +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr></tbody></table>",
                stepFunction: addColumn("before"),
                contentAfter:
                    '<table style="width: 150px;"><tbody><tr style="height: 20px;">' +
                    '<td style="width: 32px;"><p><br></p></td>' +
                    '<td style="width: 32px;">ab[]</td>' +
                    '<td style="width: 40px;">cd</td>' +
                    '<td style="width: 45px;">ef</td>' +
                    "</tr>" +
                    '<tr style="height: 30px;">' +
                    "<td><p><br></p></td>" +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr></tbody></table>",
            });
        });

        test("should add a `TH` column before", async () => {
            await testEditor({
                contentBefore:
                    '<table style="width: 150px;"><tbody><tr style="height: 20px;">' +
                    '<th style="width: 40px;">ab[]</th>' +
                    '<th style="width: 50px;">cd</th>' +
                    '<th style="width: 60px;">ef</th>' +
                    "</tr>" +
                    '<tr style="height: 30px;">' +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr></tbody></table>",
                stepFunction: addColumn("before"),
                contentAfter:
                    '<table style="width: 150px;"><tbody><tr style="height: 20px;">' +
                    '<th style="width: 32px;"><p><br></p></th>' +
                    '<th style="width: 32px;">ab[]</th>' +
                    '<th style="width: 40px;">cd</th>' +
                    '<th style="width: 45px;">ef</th>' +
                    "</tr>" +
                    '<tr style="height: 30px;">' +
                    "<td><p><br></p></td>" +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr></tbody></table>",
            });
        });

        test("should add a column left of the middle column", async () => {
            await testEditor({
                contentBefore:
                    '<table style="width: 200px;"><tbody><tr style="height: 20px;">' +
                    '<td style="width: 50px;">ab</td>' +
                    '<td style="width: 65px;">cd</td>' +
                    '<td style="width: 85px;">ef</td>' +
                    "</tr>" +
                    '<tr style="height: 30px;">' +
                    "<td>ab</td>" +
                    "<td>cd[]</td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    '<tr style="height: 40px;">' +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr></tbody></table>",
                stepFunction: addColumn("before"),
                contentAfter:
                    '<table style="width: 200px;"><tbody><tr style="height: 20px;">' +
                    '<td style="width: 38px;">ab</td>' +
                    '<td style="width: 49px;"><p><br></p></td>' +
                    '<td style="width: 49px;">cd</td>' +
                    '<td style="width: 63px;">ef</td>' +
                    "</tr>" +
                    '<tr style="height: 30px;">' +
                    "<td>ab</td>" +
                    "<td><p><br></p></td>" +
                    "<td>cd[]</td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    '<tr style="height: 40px;">' +
                    "<td>ab</td>" +
                    "<td><p><br></p></td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr></tbody></table>",
            });
        });
    });

    describe("right", () => {
        test("should add a column right of the rightmost column", async () => {
            await testEditor({
                contentBefore:
                    '<table style="width: 150px;"><tbody><tr style="height: 20px;">' +
                    '<td style="width: 40px;">ab</td>' +
                    '<td style="width: 50px;">cd</td>' +
                    '<td style="width: 60px;">ef[]</td>' +
                    "</tr>" +
                    '<tr style="height: 30px;">' +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr></tbody></table>",
                stepFunction: addColumn("after"),
                contentAfter:
                    '<table style="width: 150px;"><tbody><tr style="height: 20px;">' +
                    '<td style="width: 29px;">ab</td>' +
                    '<td style="width: 36px;">cd</td>' +
                    '<td style="width: 41px;">ef[]</td>' +
                    // size was slightly adjusted to
                    // preserve table width in view on
                    // fractional division results
                    '<td style="width: 43px;"><p><br></p></td>' +
                    "</tr>" +
                    '<tr style="height: 30px;">' +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "<td><p><br></p></td>" +
                    "</tr></tbody></table>",
            });
        });

        test("should add a `TH` column after", async () => {
            await testEditor({
                contentBefore:
                    '<table style="width: 150px;"><tbody><tr style="height: 20px;">' +
                    '<th style="width: 40px;">ab</th>' +
                    '<th style="width: 50px;">cd[]</th>' +
                    '<th style="width: 60px;">ef</th>' +
                    "</tr>" +
                    '<tr style="height: 30px;">' +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr></tbody></table>",
                stepFunction: addColumn("after"),
                contentAfter:
                    '<table style="width: 150px;"><tbody><tr style="height: 20px;">' +
                    '<th style="width: 30px;">ab</th>' +
                    '<th style="width: 38px;">cd[]</th>' +
                    '<th style="width: 38px;"><p><br></p></th>' +
                    '<th style="width: 43px;">ef</th>' +
                    "</tr>" +
                    '<tr style="height: 30px;">' +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td><p><br></p></td>" +
                    "<td>ef</td>" +
                    "</tr></tbody></table>",
            });
        });

        test("should add a column right of the middle column", async () => {
            await testEditor({
                contentBefore:
                    '<table style="width: 200px;"><tbody><tr style="height: 20px;">' +
                    '<td style="width: 50px;">ab</td>' +
                    '<td style="width: 65px;">cd</td>' +
                    '<td style="width: 85px;">ef</td>' +
                    "</tr>" +
                    '<tr style="height: 30px;">' +
                    "<td>ab</td>" +
                    "<td>cd[]</td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    '<tr style="height: 40px;">' +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr></tbody></table>",
                stepFunction: addColumn("after"),
                contentAfter:
                    '<table style="width: 200px;"><tbody><tr style="height: 20px;">' +
                    '<td style="width: 38px;">ab</td>' +
                    '<td style="width: 49px;">cd</td>' +
                    '<td style="width: 49px;"><p><br></p></td>' +
                    '<td style="width: 63px;">ef</td>' +
                    "</tr>" +
                    '<tr style="height: 30px;">' +
                    "<td>ab</td>" +
                    "<td>cd[]</td>" +
                    "<td><p><br></p></td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    '<tr style="height: 40px;">' +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td><p><br></p></td>" +
                    "<td>ef</td>" +
                    "</tr></tbody></table>",
            });
        });
    });
    describe("removal", () => {
        test("should remove a column based on selection", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td>[]ab</td> <td>cd</td>
                            </tr>
                            <tr>
                                <td>ef</td> <td>gh</td>
                            </tr>
                        </tbody>
                    </table>
                `),
                stepFunction: removeColumn(),
                contentAfter: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td>[]cd</td>
                            </tr>
                            <tr>
                                <td>gh</td>
                            </tr>
                        </tbody>
                    </table>
                `),
            });
        });
        test("should remove the column passed as argument", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td>[]ab</td> <td>cd</td>
                            </tr>
                            <tr>
                                <td>ef</td> <td>gh</td>
                            </tr>
                        </tbody>
                    </table>
                `),
                stepFunction: (editor) => {
                    // Select the second cell
                    const cell = editor.editable.querySelectorAll("td")[1];
                    removeColumn(cell)(editor);
                },
                contentAfter: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td>[]ab</td>
                            </tr>
                            <tr>
                                <td>ef</td>
                            </tr>
                        </tbody>
                    </table>
                `),
            });
        });
        test("should remove the table upon sole column removal", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <table>
                        <tbody>
                            <tr> <td>[]ab</td> </tr>
                            <tr> <td>cd</td> </tr>
                        </tbody>
                    </table>
                `),
                contentBeforeEdit: unformat(
                    `<p data-selection-placeholder=""><br></p>
                    <table>
                        <tbody>
                            <tr> <td>[]ab</td> </tr>
                            <tr> <td>cd</td> </tr>
                        </tbody>
                    </table>
                    <p data-selection-placeholder=""><br></p>`
                ),
                stepFunction: removeColumn(),
                contentAfter: "<p>[]<br></p>",
            });
        });
    });
});

describe("tab", () => {
    test("should add a new row on press tab at the end of a table", async () => {
        const contentBefore = unformat(`
            <table><tbody>
                <tr style="height: 20px;">
                    <td style="width: 20px;">ab</td>
                    <td>cd</td>
                    <td>ef[]</td>
                </tr>
            </tbody></table>`);
        const { el, editor } = await setupEditor(contentBefore);

        await press("Tab");

        const expectedContent = unformat(
            `<p data-selection-placeholder=""><br></p>
            <table><tbody>
                <tr style="height: 20px;">
                    <td style="width: 20px;">ab</td>
                    <td>cd</td>
                    <td>ef</td>
                </tr>
                <tr style="height: 20px;">
                    <td><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p></td>
                    <td><p><br></p></td>
                    <td><p><br></p></td>
                </tr>
            </tbody></table>
            <p data-selection-placeholder=""><br></p>`
        );

        expect(getContent(el)).toBe(expectedContent);

        // Check that it was registed as a history step.
        undo(editor);
        expect(getContent(el)).toBe(
            '<p data-selection-placeholder=""><br></p>' +
                contentBefore +
                '<p data-selection-placeholder=""><br></p>'
        );
    });

    test("should not select whole text of the next cell", async () => {
        await testEditor({
            contentBefore:
                '<table><tbody><tr style="height: 20px;"><td style="width: 20px;">ab</td><td>[cd]</td><td>ef</td></tr></tbody></table>',
            stepFunction: () => press("Tab"),
            contentAfter:
                '<table><tbody><tr style="height: 20px;"><td style="width: 20px;">ab</td><td>cd</td><td>ef[]</td></tr></tbody></table>',
        });
    });
});
