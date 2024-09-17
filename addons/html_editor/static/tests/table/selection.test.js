import { describe, expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { bold, resetSize, setColor, insertText } from "../_helpers/user_actions";
import { getContent, setSelection } from "../_helpers/selection";
import { press, queryAll, manuallyDispatchProgrammaticEvent } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { nodeSize } from "@html_editor/utils/position";

function expectContentToBe(el, html) {
    expect(getContent(el)).toBe(unformat(html));
}

describe("custom selection", () => {
    test("should indicate selected cells with blue background", async () => {
        const { el } = await setupEditor(
            unformat(`
            <table>
                <tbody>
                    <tr>
                        <td>ab</td>
                        <td>c[d</td>
                        <td>e]f</td>
                    </tr>
                </tbody>
            </table>`)
        );
        expect(getContent(el)).toBe(
            unformat(`
            <table class="o_selected_table">
                <tbody>
                    <tr>
                        <td>ab</td>
                        <td class="o_selected_td">c[d</td>
                        <td class="o_selected_td">e]f</td>
                    </tr>
                </tbody>
            </table>`)
        );
        const defaultBackgroundColor = getComputedStyle(el)["background-color"];
        const backgroundColorTDs = queryAll("table td").map(
            (td) => getComputedStyle(td)["background-color"]
        );
        // Unselected cells should have the default background color
        expect(backgroundColorTDs[0]).toBe(defaultBackgroundColor);
        // Selected cells should have a distinct background color
        expect(backgroundColorTDs[1]).not.toBe(defaultBackgroundColor);
        expect(backgroundColorTDs[2]).not.toBe(defaultBackgroundColor);
    });
});

describe("select a full table on cross over", () => {
    describe("select", () => {
        test("should select some characters and a table", async () => {
            await testEditor({
                contentBefore:
                    "<p>a[bc</p><table><tbody><tr><td>a]b</td><td>cd</td><td>ef</td></tr></tbody></table>",
                contentAfterEdit:
                    "<p>a[bc</p>" +
                    '<table class="o_selected_table"><tbody><tr>' +
                    '<td class="o_selected_td">ab</td>' +
                    '<td class="o_selected_td">cd</td>' +
                    '<td class="o_selected_td">ef]</td>' +
                    "</tr></tbody></table>",
            });
        });

        test("should select a table and some characters", async () => {
            await testEditor({
                contentBefore:
                    "<table><tbody><tr><td>ab</td><td>cd</td><td>e[f</td></tr></tbody></table><p>a]bc</p>",
                contentAfterEdit:
                    '<table class="o_selected_table"><tbody><tr>' +
                    '<td class="o_selected_td">ab</td>' +
                    '<td class="o_selected_td">cd</td>' +
                    '<td class="o_selected_td">e[f</td></tr></tbody></table><p>a]bc</p>',
            });
        });

        test("should select some characters, a table and some more characters", async () => {
            await testEditor({
                contentBefore:
                    "<p>a[bc</p><table><tbody><tr><td>ab</td><td>cd</td><td>ef</td></tr></tbody></table><p>a]bc</p>",
                contentAfterEdit:
                    '<p>a[bc</p><table class="o_selected_table"><tbody><tr>' +
                    '<td class="o_selected_td">ab</td>' +
                    '<td class="o_selected_td">cd</td>' +
                    '<td class="o_selected_td">ef</td></tr></tbody></table><p>a]bc</p>',
            });
        });

        test("should select some characters, a table, some more characters and another table", async () => {
            await testEditor({
                contentBefore:
                    "<p>a[bc</p><table><tbody><tr><td>ab</td><td>cd</td><td>ef</td></tr></tbody></table><p>abc</p><table><tbody><tr><td>a]b</td><td>cd</td><td>ef</td></tr></tbody></table>",
                contentAfterEdit:
                    '<p>a[bc</p><table class="o_selected_table"><tbody><tr>' +
                    '<td class="o_selected_td">ab</td>' +
                    '<td class="o_selected_td">cd</td>' +
                    '<td class="o_selected_td">ef</td></tr></tbody></table>' +
                    '<p>abc</p><table class="o_selected_table"><tbody><tr>' +
                    '<td class="o_selected_td">ab</td>' +
                    '<td class="o_selected_td">cd</td>' +
                    '<td class="o_selected_td">ef]</td></tr></tbody></table>',
            });
        });

        test("should select some characters, a table, some more characters, another table and some more characters", async () => {
            await testEditor({
                contentBefore:
                    "<p>a[bc</p><table><tbody><tr><td>ab</td><td>cd</td><td>ef</td></tr></tbody></table><p>abc</p><table><tbody><tr><td>ab</td><td>cd</td><td>ef</td></tr></tbody></table><p>a]bc</p>",
                contentAfterEdit:
                    '<p>a[bc</p><table class="o_selected_table"><tbody><tr>' +
                    '<td class="o_selected_td">ab</td>' +
                    '<td class="o_selected_td">cd</td>' +
                    '<td class="o_selected_td">ef</td></tr></tbody></table>' +
                    '<p>abc</p><table class="o_selected_table"><tbody><tr>' +
                    '<td class="o_selected_td">ab</td>' +
                    '<td class="o_selected_td">cd</td>' +
                    '<td class="o_selected_td">ef</td></tr></tbody></table><p>a]bc</p>',
            });
        });
    });

    describe("toggleFormat", () => {
        test("should apply bold to some characters and a table", async () => {
            await testEditor({
                contentBefore:
                    "<p>a[bc</p><table><tbody><tr>" +
                    "<td>a]b</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr></tbody></table>",
                stepFunction: bold,
                contentAfterEdit:
                    "<p>a<strong>[bc</strong></p>" +
                    '<table class="o_selected_table"><tbody><tr>' +
                    '<td class="o_selected_td"><strong>ab</strong></td>' +
                    '<td class="o_selected_td"><strong>cd</strong></td>' +
                    '<td class="o_selected_td"><strong>ef]</strong></td>' +
                    "</tr></tbody></table>",
            });
        });

        test("should apply bold to a table and some characters", async () => {
            await testEditor({
                contentBefore:
                    "<table><tbody><tr>" +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>e[f</td>" +
                    "</tr></tbody></table><p>a]bc</p>",
                stepFunction: bold,
                contentAfterEdit:
                    '<table class="o_selected_table"><tbody><tr>' +
                    '<td class="o_selected_td"><strong>[ab</strong></td>' +
                    '<td class="o_selected_td"><strong>cd</strong></td>' +
                    '<td class="o_selected_td"><strong>ef</strong></td>' +
                    "</tr></tbody></table>" +
                    "<p><strong>a]</strong>bc</p>",
            });
        });

        test("should apply bold to some characters, a table and some more characters", async () => {
            await testEditor({
                contentBefore:
                    "<p>a[bc</p>" +
                    "<table><tbody><tr>" +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr></tbody></table>" +
                    "<p>a]bc</p>",
                stepFunction: bold,
                contentAfterEdit:
                    "<p>a<strong>[bc</strong></p>" +
                    '<table class="o_selected_table"><tbody><tr>' +
                    '<td class="o_selected_td"><strong>ab</strong></td>' +
                    '<td class="o_selected_td"><strong>cd</strong></td>' +
                    '<td class="o_selected_td"><strong>ef</strong></td>' +
                    "</tr></tbody></table>" +
                    "<p><strong>a]</strong>bc</p>",
            });
        });

        test("should apply bold to some characters, a table, some more characters and another table", async () => {
            await testEditor({
                contentBefore:
                    "<p>a[bc</p>" +
                    "<table><tbody><tr>" +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr></tbody></table>" +
                    "<p>abc</p>" +
                    "<table><tbody><tr>" +
                    "<td>a]b</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr></tbody></table>",
                stepFunction: bold,
                contentAfterEdit:
                    "<p>a<strong>[bc</strong></p>" +
                    '<table class="o_selected_table"><tbody><tr>' +
                    '<td class="o_selected_td"><strong>ab</strong></td>' +
                    '<td class="o_selected_td"><strong>cd</strong></td>' +
                    '<td class="o_selected_td"><strong>ef</strong></td>' +
                    "</tr></tbody></table>" +
                    "<p><strong>abc</strong></p>" +
                    '<table class="o_selected_table"><tbody><tr>' +
                    '<td class="o_selected_td"><strong>ab</strong></td>' +
                    '<td class="o_selected_td"><strong>cd</strong></td>' +
                    '<td class="o_selected_td"><strong>ef]</strong></td>' +
                    "</tr></tbody></table>",
            });
        });

        test("should apply bold to some characters, a table, some more characters, another table and some more characters", async () => {
            await testEditor({
                contentBefore:
                    "<p>a[bc</p>" +
                    "<table><tbody><tr>" +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr></tbody></table>" +
                    "<p>abc</p>" +
                    "<table><tbody><tr>" +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr></tbody></table>" +
                    "<p>a]bc</p>",
                stepFunction: bold,
                contentAfterEdit:
                    "<p>a<strong>[bc</strong></p>" +
                    '<table class="o_selected_table"><tbody><tr>' +
                    '<td class="o_selected_td"><strong>ab</strong></td>' +
                    '<td class="o_selected_td"><strong>cd</strong></td>' +
                    '<td class="o_selected_td"><strong>ef</strong></td>' +
                    "</tr></tbody></table>" +
                    "<p><strong>abc</strong></p>" +
                    '<table class="o_selected_table"><tbody><tr>' +
                    '<td class="o_selected_td"><strong>ab</strong></td>' +
                    '<td class="o_selected_td"><strong>cd</strong></td>' +
                    '<td class="o_selected_td"><strong>ef</strong></td>' +
                    "</tr></tbody></table>" +
                    "<p><strong>a]</strong>bc</p>",
            });
        });
    });

    describe("color", () => {
        test("should apply a color to some characters and a table", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <p>a[bc</p>
                    <table>
                        <tbody>
                            <tr>
                                <td>a]b</td>
                                <td>cd</td>
                                <td>ef</td>
                            </tr>
                        </tbody>
                    </table>`),
                stepFunction: setColor("aquamarine", "color"),
                contentAfterEdit: unformat(`
                    <p>
                        a<font style="color: aquamarine;">[bc</font>
                    </p>
                    <table class="o_selected_table">
                        <tbody>
                            <tr>
                                <td class="o_selected_td">
                                    <font style="color: aquamarine;">ab</font>
                                </td>
                                <td class="o_selected_td">
                                    <font style="color: aquamarine;">cd</font>
                                </td>
                                <td class="o_selected_td">
                                    <font style="color: aquamarine;">ef]</font>
                                </td>
                            </tr>
                        </tbody>
                    </table>`),
            });
        });

        test("should apply a color to a table and some characters", async () => {
            await testEditor({
                contentBefore:
                    "<table><tbody><tr>" +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>e[f</td>" +
                    "</tr></tbody></table><p>a]bc</p>",
                stepFunction: setColor("aquamarine", "color"),
                contentAfterEdit: unformat(`
                    <table class="o_selected_table">
                        <tbody><tr>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">ab</font>
                            </td>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">cd</font>
                            </td>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">e[f</font>
                            </td>
                        </tr></tbody>
                    </table>
                    <p>
                        <font style="color: aquamarine;">a]</font>bc
                    </p>`),
            });
        });

        test("should apply a color to some characters, a table and some more characters", async () => {
            await testEditor({
                contentBefore:
                    "<p>a[bc</p>" +
                    "<table><tbody><tr>" +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr></tbody></table>" +
                    "<p>a]bc</p>",
                stepFunction: setColor("aquamarine", "color"),
                contentAfterEdit: unformat(`
                    <p>
                        a<font style="color: aquamarine;">[bc</font>
                    </p>
                    <table class="o_selected_table">
                        <tbody><tr>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">ab</font>
                            </td>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">cd</font>
                            </td>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">ef</font>
                            </td>
                        </tr></tbody>
                    </table>
                    <p>
                        <font style="color: aquamarine;">a]</font>bc
                    </p>`),
            });
        });

        test("should apply a color to some characters, a table, some more characters and another table", async () => {
            await testEditor({
                contentBefore:
                    "<p>a[bc</p>" +
                    "<table><tbody><tr>" +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr></tbody></table>" +
                    "<p>abc</p>" +
                    "<table><tbody><tr>" +
                    "<td>a]b</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr></tbody></table>",
                stepFunction: setColor("aquamarine", "color"),
                contentAfterEdit: unformat(`
                    <p>
                        a<font style="color: aquamarine;">[bc</font>
                    </p>
                    <table class="o_selected_table">
                        <tbody><tr>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">ab</font>
                            </td>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">cd</font>
                            </td>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">ef</font>
                            </td>
                        </tr></tbody>
                    </table>
                    <p>
                        <font style="color: aquamarine;">abc</font>
                    </p>
                    <table class="o_selected_table">
                        <tbody><tr>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">ab</font>
                            </td>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">cd</font>
                            </td>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">ef]</font>
                            </td>
                        </tr></tbody>
                    </table>`),
            });
        });

        test("should apply a color to some characters, a table, some more characters, another table and some more characters", async () => {
            await testEditor({
                contentBefore:
                    "<p>a[bc</p>" +
                    "<table><tbody><tr>" +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr></tbody></table>" +
                    "<p>abc</p>" +
                    "<table><tbody><tr>" +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr></tbody></table>" +
                    "<p>a]bc</p>",
                stepFunction: setColor("aquamarine", "color"),
                contentAfterEdit: unformat(`
                    <p>
                        a<font style="color: aquamarine;">[bc</font>
                    </p>
                    <table class="o_selected_table">
                        <tbody><tr>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">ab</font>
                            </td>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">cd</font>
                            </td>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">ef</font>
                            </td>
                        </tr></tbody>
                    </table>
                    <p><font style="color: aquamarine;">abc</font></p>
                    <table class="o_selected_table">
                        <tbody><tr>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">ab</font>
                            </td>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">cd</font>
                            </td>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">ef</font>
                            </td>
                        </tr></tbody>
                    </table>
                    <p><font style="color: aquamarine;">a]</font>bc</p>`),
            });
        });
    });
});

describe("select columns on cross over", () => {
    describe("select", () => {
        test("should select two columns", async () => {
            await testEditor({
                contentBefore:
                    "<table><tbody><tr><td>a[b</td><td>c]d</td><td>ef</td></tr></tbody></table>",
                contentAfterEdit:
                    '<table class="o_selected_table"><tbody><tr>' +
                    '<td class="o_selected_td">a[b</td>' +
                    '<td class="o_selected_td">c]d</td>' +
                    "<td>ef</td>" +
                    "</tr></tbody></table>",
            });
        });

        test("should select a whole row", async () => {
            await testEditor({
                contentBefore:
                    "<table><tbody><tr><td>a[b</td><td>cd</td><td>e]f</td></tr><tr><td>ab</td><td>cd</td><td>ef</td></tr></tbody></table>",
                contentAfterEdit:
                    '<table class="o_selected_table"><tbody><tr>' +
                    '<td class="o_selected_td">a[b</td>' +
                    '<td class="o_selected_td">cd</td>' +
                    '<td class="o_selected_td">e]f</td>' +
                    "</tr><tr><td>ab</td><td>cd</td><td>ef</td></tr></tbody></table>",
            });
        });

        test("should select a whole column", async () => {
            await testEditor({
                contentBefore:
                    "<table><tbody>" +
                    "<tr><td>a[b</td><td>cd</td><td>ef</td></tr>" +
                    "<tr><td>ab</td><td>cd</td><td>ef</td></tr>" +
                    "<tr><td>a]b</td><td>cd</td><td>ef</td></tr>" +
                    "</tbody></table>",
                contentAfterEdit:
                    '<table class="o_selected_table"><tbody>' +
                    "<tr>" +
                    '<td class="o_selected_td">a[b</td>' +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    "<tr>" +
                    '<td class="o_selected_td">ab</td>' +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    "<tr>" +
                    '<td class="o_selected_td">a]b</td>' +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    "</tbody></table>",
            });
        });

        test("should select from (0,0) to (1,1) in a 3x3 table", async () => {
            await testEditor({
                contentBefore:
                    "<table><tbody>" +
                    "<tr><td>a[b</td><td>cd</td><td>ef</td></tr>" +
                    "<tr><td>ab</td><td>c]d</td><td>ef</td></tr>" +
                    "<tr><td>ab</td><td>cd</td><td>ef</td></tr>" +
                    "</tbody></table>",
                contentAfterEdit:
                    '<table class="o_selected_table"><tbody>' +
                    "<tr>" +
                    '<td class="o_selected_td">a[b</td>' +
                    '<td class="o_selected_td">cd</td>' +
                    "<td>ef</td>" +
                    "</tr>" +
                    "<tr>" +
                    '<td class="o_selected_td">ab</td>' +
                    '<td class="o_selected_td">c]d</td>' +
                    "<td>ef</td>" +
                    "</tr>" +
                    "<tr>" +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    "</tbody></table>",
            });
        });

        test("should select a whole table", async () => {
            await testEditor({
                contentBefore:
                    "<table><tbody>" +
                    "<tr><td>a[b</td><td>cd</td><td>ef</td></tr>" +
                    "<tr><td>ab</td><td>cd</td><td>ef</td></tr>" +
                    "<tr><td>ab</td><td>cd</td><td>e]f</td></tr>" +
                    "</tbody></table>",
                contentAfterEdit:
                    '<table class="o_selected_table"><tbody>' +
                    "<tr>" +
                    '<td class="o_selected_td">a[b</td>' +
                    '<td class="o_selected_td">cd</td>' +
                    '<td class="o_selected_td">ef</td>' +
                    "</tr>" +
                    "<tr>" +
                    '<td class="o_selected_td">ab</td>' +
                    '<td class="o_selected_td">cd</td>' +
                    '<td class="o_selected_td">ef</td>' +
                    "</tr>" +
                    "<tr>" +
                    '<td class="o_selected_td">ab</td>' +
                    '<td class="o_selected_td">cd</td>' +
                    '<td class="o_selected_td">e]f</td>' +
                    "</tr>" +
                    "</tbody></table>",
            });
        });
    });

    describe("toggleFormat", () => {
        test("should apply bold to two columns", async () => {
            await testEditor({
                contentBefore:
                    "<table><tbody><tr>" +
                    "<td>a[b</td>" +
                    "<td>c]d</td>" +
                    "<td>ef</td>" +
                    "</tr></tbody></table>",
                stepFunction: bold,
                contentAfterEdit:
                    '<table class="o_selected_table"><tbody><tr>' +
                    '<td class="o_selected_td"><strong>[ab</strong></td>' +
                    '<td class="o_selected_td"><strong>cd]</strong></td>' +
                    "<td>ef</td>" +
                    "</tr></tbody></table>",
            });
        });

        test("should apply bold to a whole row", async () => {
            await testEditor({
                contentBefore:
                    "<table><tbody><tr>" +
                    "<td>a[b</td>" +
                    "<td>cd</td>" +
                    "<td>e]f</td>" +
                    "</tr><tr><td>ab</td><td>cd</td><td>ef</td></tr></tbody></table>",
                stepFunction: bold,
                contentAfterEdit:
                    '<table class="o_selected_table"><tbody><tr>' +
                    '<td class="o_selected_td"><strong>[ab</strong></td>' +
                    '<td class="o_selected_td"><strong>cd</strong></td>' +
                    '<td class="o_selected_td"><strong>ef]</strong></td>' +
                    "</tr><tr><td>ab</td><td>cd</td><td>ef</td></tr></tbody></table>",
            });
        });

        test("should apply bold to a whole column", async () => {
            await testEditor({
                contentBefore:
                    "<table><tbody>" +
                    "<tr>" +
                    "<td>a[b</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    "<tr>" +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    "<tr>" +
                    "<td>a]b</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    "</tbody></table>",
                stepFunction: bold,
                contentAfterEdit:
                    '<table class="o_selected_table"><tbody>' +
                    "<tr>" +
                    '<td class="o_selected_td"><strong>[ab</strong></td>' +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    "<tr>" +
                    '<td class="o_selected_td"><strong>ab</strong></td>' +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    "<tr>" +
                    '<td class="o_selected_td"><strong>ab]</strong></td>' +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    "</tbody></table>",
            });
        });

        test("should apply bold from (0,0) to (1,1) in a 3x3 table", async () => {
            await testEditor({
                contentBefore:
                    "<table><tbody>" +
                    "<tr>" +
                    "<td>a[b</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    "<tr>" +
                    "<td>ab</td>" +
                    "<td>c]d</td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    "<tr>" +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    "</tbody></table>",
                stepFunction: bold,
                contentAfterEdit:
                    '<table class="o_selected_table"><tbody>' +
                    "<tr>" +
                    '<td class="o_selected_td"><strong>[ab</strong></td>' +
                    '<td class="o_selected_td"><strong>cd</strong></td>' +
                    "<td>ef</td>" +
                    "</tr>" +
                    "<tr>" +
                    '<td class="o_selected_td"><strong>ab</strong></td>' +
                    '<td class="o_selected_td"><strong>cd]</strong></td>' +
                    "<td>ef</td>" +
                    "</tr>" +
                    "<tr>" +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    "</tbody></table>",
            });
        });

        test("should apply bold to a whole table", async () => {
            await testEditor({
                contentBefore:
                    "<table><tbody>" +
                    "<tr>" +
                    "<td>a[b</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    "<tr>" +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    "<tr>" +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>e]f</td>" +
                    "</tr>" +
                    "</tbody></table>",
                stepFunction: bold,
                contentAfterEdit:
                    '<table class="o_selected_table"><tbody>' +
                    "<tr>" +
                    '<td class="o_selected_td"><strong>[ab</strong></td>' +
                    '<td class="o_selected_td"><strong>cd</strong></td>' +
                    '<td class="o_selected_td"><strong>ef</strong></td>' +
                    "</tr>" +
                    "<tr>" +
                    '<td class="o_selected_td"><strong>ab</strong></td>' +
                    '<td class="o_selected_td"><strong>cd</strong></td>' +
                    '<td class="o_selected_td"><strong>ef</strong></td>' +
                    "</tr>" +
                    "<tr>" +
                    '<td class="o_selected_td"><strong>ab</strong></td>' +
                    '<td class="o_selected_td"><strong>cd</strong></td>' +
                    '<td class="o_selected_td"><strong>ef]</strong></td>' +
                    "</tr>" +
                    "</tbody></table>",
            });
        });
    });

    describe("reset size", () => {
        test("should remove any height or width of the table and bring it back to it original form", async () => {
            await testEditor({
                contentBefore: `<table class="table table-bordered o_table" style="height: 980.5px; width: 736px;"><tbody>
                                    <tr style="height: 306.5px;">
                                        <td style="width: 356px;"><p>[]<br></p></td>
                                        <td style="width: 108.5px;"><p><br></p></td>
                                        <td style="width: 232.25px;"><p><br></p></td>
                                        <td style="width: 38.25px;"><p><br></p></td>
                                    </tr>
                                    <tr style="height: 252px;">
                                        <td style="width: 232.25px;"><p><br></p></td>
                                        <td style="width: 232.25px;"><p><br></p></td>
                                        <td style="width: 232.25px;"><p><br></p></td>
                                        <td style="width: 232.25px;"><p><br></p></td>
                                    </tr>
                                    <tr style="height: 57px;">
                                        <td style="width: 232.25px;"><p><br></p></td>
                                        <td style="width: 232.25px;"><p><br></p></td>
                                        <td style="width: 232.25px;"><p><br></p></td>
                                        <td style="width: 232.25px;"><p><br></p></td>
                                    </tr>
                                </tbody></table>`,
                stepFunction: resetSize,
                contentAfter: `<table class="table table-bordered o_table"><tbody>
                                    <tr>
                                        <td><p>[]<br></p></td>
                                        <td><p><br></p></td>
                                        <td><p><br></p></td>
                                        <td><p><br></p></td>
                                    </tr>
                                    <tr>
                                        <td><p><br></p></td>
                                        <td><p><br></p></td>
                                        <td><p><br></p></td>
                                        <td><p><br></p></td>
                                    </tr>
                                    <tr>
                                        <td><p><br></p></td>
                                        <td><p><br></p></td>
                                        <td><p><br></p></td>
                                        <td><p><br></p></td>
                                    </tr>
                                </tbody></table>`,
            });
        });

        test("should remove any height or width of the table without loosing the style of the element inside it.", async () => {
            await testEditor({
                contentBefore: `<table class="table table-bordered o_table" style="width: 472.182px; height: 465.403px;"><tbody>
                                    <tr style="height: 104.872px;">
                                        <td style="width: 191.273px;"><h1>[]TESTTEXT</h1></td>
                                        <td style="width: 154.009px;"><p><br></p></td>
                                        <td style="width: 126.003px;">
                                            <ul>
                                                <li>test</li>
                                                <li>test</li>
                                                <li>test</li>
                                            </ul>
                                        </td>
                                    </tr>
                                    <tr style="height: 254.75px;">
                                        <td style="width: 229.673px;"><p><br></p></td>
                                        <td style="width: 229.687px;">
                                            <blockquote>TESTTEXT</blockquote>
                                        </td>
                                        <td style="width: 229.73px;"><p><br></p></td>
                                    </tr>
                                    <tr style="height: 104.872px;">
                                        <td style="width: 229.673px;"><pre>codeTEST</pre></td>
                                        <td style="width: 229.687px;"><p><br></p></td>
                                        <td style="width: 229.73px;">
                                            <ol>
                                                <li>text</li>
                                                <li>text</li>
                                                <li>text</li>
                                            </ol>
                                            </td>
                                    </tr></tbody></table>`,
                stepFunction: resetSize,
                contentAfter: `<table class="table table-bordered o_table"><tbody>
                                    <tr>
                                        <td><h1>[]TESTTEXT</h1></td>
                                        <td><p><br></p></td>
                                        <td>
                                            <ul>
                                                <li>test</li>
                                                <li>test</li>
                                                <li>test</li>
                                            </ul>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td><p><br></p></td>
                                        <td>
                                            <blockquote>TESTTEXT</blockquote>
                                        </td>
                                        <td><p><br></p></td>
                                    </tr>
                                    <tr>
                                        <td><pre>codeTEST</pre></td>
                                        <td><p><br></p></td>
                                        <td>
                                            <ol>
                                                <li>text</li>
                                                <li>text</li>
                                                <li>text</li>
                                            </ol>
                                            </td>
                                    </tr></tbody></table>`,
            });
        });

        test("should remove any height or width of the table without removig the style of the table.", async () => {
            await testEditor({
                contentBefore: `<table class="table table-bordered o_table" style="height: 594.5px; width: 807px;"><tbody>
                                    <tr style="height: 229.5px;">
                                        <td style="background-color: rgb(206, 231, 247); color: rgb(0, 0, 255); width: 500px;"><p>[]<br></p></td>
                                        <td style="background-color: rgb(206, 231, 247); color: rgb(0, 0, 255); width: 119.328px;"><p><br></p></td>
                                        <td style="background-color: rgb(206, 231, 247); color: rgb(0, 0, 255); width: 186.672px;"><p><br></p></td>
                                    </tr>
                                    <tr style="height: 260px;">
                                        <td style="background-color: rgb(206, 231, 247); color: rgb(0, 0, 255); width: 309.656px;"><p><br></p></td>
                                        <td style="background-color: rgb(206, 231, 247); color: rgb(0, 0, 255); width: 309.672px;"><p><br></p></td>
                                        <td style="background-color: rgb(206, 231, 247); color: rgb(0, 0, 255); width: 309.672px;"><p><br></p></td>
                                    </tr>
                                    <tr style="height: 104px;">
                                        <td style="background-color: rgb(206, 231, 247); color: rgb(0, 0, 255); width: 309.656px;"><p><br></p></td>
                                        <td style="background-color: rgb(206, 231, 247); color: rgb(0, 0, 255); width: 309.672px;"><p><br></p></td>
                                        <td style="background-color: rgb(206, 231, 247); color: rgb(0, 0, 255); width: 309.672px;"><p><br></p></td>
                                    </tr>
                                </tbody></table>`,
                stepFunction: resetSize,
                contentAfter: `<table class="table table-bordered o_table"><tbody>
                                    <tr>
                                        <td style="background-color: rgb(206, 231, 247); color: rgb(0, 0, 255);"><p>[]<br></p></td>
                                        <td style="background-color: rgb(206, 231, 247); color: rgb(0, 0, 255);"><p><br></p></td>
                                        <td style="background-color: rgb(206, 231, 247); color: rgb(0, 0, 255);"><p><br></p></td>
                                    </tr>
                                    <tr>
                                        <td style="background-color: rgb(206, 231, 247); color: rgb(0, 0, 255);"><p><br></p></td>
                                        <td style="background-color: rgb(206, 231, 247); color: rgb(0, 0, 255);"><p><br></p></td>
                                        <td style="background-color: rgb(206, 231, 247); color: rgb(0, 0, 255);"><p><br></p></td>
                                    </tr>
                                    <tr>
                                        <td style="background-color: rgb(206, 231, 247); color: rgb(0, 0, 255);"><p><br></p></td>
                                        <td style="background-color: rgb(206, 231, 247); color: rgb(0, 0, 255);"><p><br></p></td>
                                        <td style="background-color: rgb(206, 231, 247); color: rgb(0, 0, 255);"><p><br></p></td>
                                    </tr>
                                </tbody></table>`,
            });
        });
    });

    describe("color", () => {
        test("should apply a color to two columns", async () => {
            await testEditor({
                contentBefore:
                    "<table><tbody><tr>" +
                    "<td>a[b</td>" +
                    "<td>c]d</td>" +
                    "<td>ef</td>" +
                    "</tr></tbody></table>",
                stepFunction: setColor("aquamarine", "color"),
                contentAfterEdit: unformat(`
                    <table class="o_selected_table">
                        <tbody><tr>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">a[b</font>
                            </td>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">c]d</font>
                            </td>
                            <td>ef</td>
                        </tr></tbody>
                    </table>`),
            });
        });

        test("should apply a color to a whole row", async () => {
            await testEditor({
                contentBefore:
                    "<table><tbody><tr>" +
                    "<td>a[b</td>" +
                    "<td>cd</td>" +
                    "<td>e]f</td>" +
                    "</tr><tr><td>ab</td><td>cd</td><td>ef</td></tr></tbody></table>",
                stepFunction: setColor("aquamarine", "color"),
                contentAfterEdit: unformat(`
                    <table class="o_selected_table">
                        <tbody><tr>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">a[b</font>
                            </td>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">cd</font>
                            </td>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">e]f</font>
                            </td>
                        </tr>
                        <tr>
                            <td>ab</td>
                            <td>cd</td>
                            <td>ef</td>
                        </tr></tbody>
                    </table>`),
            });
        });

        test("should apply a color to a whole column", async () => {
            await testEditor({
                contentBefore:
                    "<table><tbody>" +
                    "<tr>" +
                    "<td>a[b</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    "<tr>" +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    "<tr>" +
                    "<td>a]b</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    "</tbody></table>",
                stepFunction: setColor("aquamarine", "color"),
                contentAfterEdit: unformat(`
                    <table class="o_selected_table">
                        <tbody><tr>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">a[b</font>
                            </td>
                            <td>cd</td>
                            <td>ef</td>
                        </tr>
                        <tr>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">ab</font>
                            </td>
                            <td>cd</td>
                            <td>ef</td>
                        </tr>
                        <tr>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">a]b</font>
                            </td>
                            <td>cd</td>
                            <td>ef</td>
                        </tr></tbody>
                    </table>`),
            });
        });

        test("should apply a color from (0,0) to (1,1) in a 3x3 table", async () => {
            await testEditor({
                contentBefore:
                    "<table><tbody>" +
                    "<tr>" +
                    "<td>a[b</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    "<tr>" +
                    "<td>ab</td>" +
                    "<td>c]d</td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    "<tr>" +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    "</tbody></table>",
                stepFunction: setColor("aquamarine", "color"),
                contentAfterEdit: unformat(`
                    <table class="o_selected_table">
                        <tbody><tr>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">a[b</font>
                            </td>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">cd</font>
                            </td>
                            <td>ef</td>
                        </tr>
                        <tr>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">ab</font>
                            </td>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">c]d</font>
                            </td>
                            <td>ef</td>
                        </tr>
                        <tr>
                            <td>ab</td>
                            <td>cd</td>
                            <td>ef</td>
                        </tr></tbody>
                    </table>`),
            });
        });

        test("should apply a color to a whole table", async () => {
            await testEditor({
                contentBefore:
                    "<table><tbody>" +
                    "<tr>" +
                    "<td>a[b</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    "<tr>" +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>ef</td>" +
                    "</tr>" +
                    "<tr>" +
                    "<td>ab</td>" +
                    "<td>cd</td>" +
                    "<td>e]f</td>" +
                    "</tr>" +
                    "</tbody></table>",
                stepFunction: setColor("aquamarine", "color"),
                contentAfterEdit: unformat(`
                    <table class="o_selected_table">
                        <tbody><tr>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">a[b</font>
                            </td>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">cd</font>
                            </td>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">ef</font>
                            </td>
                        </tr>
                        <tr>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">ab</font>
                            </td>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">cd</font>
                            </td>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">ef</font>
                            </td>
                        </tr>
                        <tr>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">ab</font>
                            </td>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">cd</font>
                            </td>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">e]f</font>
                            </td>
                        </tr></tbody>
                    </table>`),
            });
        });
    });
});

describe("move cursor with arrow keys", () => {
    describe("arrowup", () => {
        test("should move cursor to the cell above", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td><br></td>
                                <td><br></td>
                            </tr>
                            <tr>
                                <td>[]<br></td>
                                <td><br></td>
                            </tr>
                        </tbody>
                    </table>
                `),
                stepFunction: async () => press("ArrowUp"),
                contentAfter: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td>[]<br></td>
                                <td><br></td>
                            </tr>
                            <tr>
                                <td><br></td>
                                <td><br></td>
                            </tr>
                        </tbody>
                    </table>
                `),
            });
        });
        test("should move cursor to the end in the cell above", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td>abc</td>
                                <td><br></td>
                            </tr>
                            <tr>
                                <td>[]<br></td>
                                <td><br></td>
                            </tr>
                        </tbody>
                    </table>
                `),
                stepFunction: async () => press("ArrowUp"),
                contentAfter: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td>abc[]</td>
                                <td><br></td>
                            </tr>
                            <tr>
                                <td><br></td>
                                <td><br></td>
                            </tr>
                        </tbody>
                    </table>
                `),
            });
            await testEditor({
                contentBefore: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td>
                                    <p>abc</p>
                                    <p>def</p>
                                </td>
                                <td><br></td>
                            </tr>
                            <tr>
                                <td>abc[]</td>
                                <td><br></td>
                            </tr>
                        </tbody>
                    </table>
                `),
                stepFunction: async () => press("ArrowUp"),
                contentAfter: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td>
                                    <p>abc</p>
                                    <p>def[]</p>
                                </td>
                                <td><br></td>
                            </tr>
                            <tr>
                                <td>abc</td>
                                <td><br></td>
                            </tr>
                        </tbody>
                    </table>
                `),
            });
        });
        test("should move cursor to the previous sibling of table", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <p>abcd</p>
                    <table>
                        <tbody>
                            <tr>
                                <td>[]<br></td>
                                <td><br></td>
                            </tr>
                            <tr>
                                <td><br></td>
                                <td><br></td>
                            </tr>
                        </tbody>
                    </table>
                `),
                stepFunction: async () => press("ArrowUp"),
                contentAfter: unformat(`
                    <p>abcd[]</p>
                    <table>
                        <tbody>
                            <tr>
                                <td><br></td>
                                <td><br></td>
                            </tr>
                            <tr>
                                <td><br></td>
                                <td><br></td>
                            </tr>
                        </tbody>
                    </table>
                `),
            });
        });
        test("should move cursor to the end cell of sibling table", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td><br></td>
                                <td><br></td>
                            </tr>
                            <tr>
                                <td><br></td>
                                <td><br></td>
                            </tr>
                        </tbody>
                    </table>
                    <table>
                        <tbody>
                            <tr>
                                <td>[]<br></td>
                                <td><br></td>
                            </tr>
                            <tr>
                                <td><br></td>
                                <td><br></td>
                            </tr>
                        </tbody>
                    </table>
                `),
                stepFunction: async () => press("ArrowUp"),
                contentAfter: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td><br></td>
                                <td><br></td>
                            </tr>
                            <tr>
                                <td><br></td>
                                <td>[]<br></td>
                            </tr>
                        </tbody>
                    </table>
                    <table>
                        <tbody>
                            <tr>
                                <td><br></td>
                                <td><br></td>
                            </tr>
                            <tr>
                                <td><br></td>
                                <td><br></td>
                            </tr>
                        </tbody>
                    </table>
                `),
            });
        });
    });

    describe("arrowdown", () => {
        test("should move cursor to the cell below", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td>[]<br></td>
                                <td><br></td>
                            </tr>
                            <tr>
                                <td><br></td>
                                <td><br></td>
                            </tr>
                        </tbody>
                    </table>
                `),
                stepFunction: async () => press("ArrowDown"),
                contentAfter: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td><br></td>
                                <td><br></td>
                            </tr>
                            <tr>
                                <td>[]<br></td>
                                <td><br></td>
                            </tr>
                        </tbody>
                    </table>
                `),
            });
        });
        test("should move cursor to the start of the cell below", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td>[]<br></td>
                                <td><br></td>
                            </tr>
                            <tr>
                                <td>abc</td>
                                <td><br></td>
                            </tr>
                        </tbody>
                    </table>
                `),
                stepFunction: async () => press("ArrowDown"),
                contentAfter: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td><br></td>
                                <td><br></td>
                            </tr>
                            <tr>
                                <td>[]abc</td>
                                <td><br></td>
                            </tr>
                        </tbody>
                    </table>
                `),
            });
            await testEditor({
                contentBefore: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td>abc[]</td>
                                <td><br></td>
                            </tr>
                            <tr>
                                <td>
                                    <p>abc</p>
                                    <p>def</p>
                                </td>
                                <td><br></td>
                            </tr>
                        </tbody>
                    </table>
                `),
                stepFunction: async () => press("ArrowDown"),
                contentAfter: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td>abc</td>
                                <td><br></td>
                            </tr>
                            <tr>
                                <td>
                                    <p>[]abc</p>
                                    <p>def</p>
                                </td>
                                <td><br></td>
                            </tr>
                        </tbody>
                    </table>
                `),
            });
        });
        test("should move cursor to the next sibling of table", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td><br></td>
                                <td><br></td>
                            </tr>
                            <tr>
                                <td>[]<br></td>
                                <td><br></td>
                            </tr>
                        </tbody>
                    </table>
                    <p>abcd</p>
                `),
                stepFunction: async () => press("ArrowDown"),
                contentAfter: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td><br></td>
                                <td><br></td>
                            </tr>
                            <tr>
                                <td><br></td>
                                <td><br></td>
                            </tr>
                        </tbody>
                    </table>
                    <p>[]abcd</p>
                `),
            });
        });
        test("should move cursor to the first cell of sibling table", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td><br></td>
                                <td><br></td>
                            </tr>
                            <tr>
                                <td>[]<br></td>
                                <td><br></td>
                            </tr>
                        </tbody>
                    </table>
                    <table>
                        <tbody>
                            <tr>
                                <td><br></td>
                                <td><br></td>
                            </tr>
                            <tr>
                                <td><br></td>
                                <td><br></td>
                            </tr>
                        </tbody>
                    </table>
                `),
                stepFunction: async () => press("ArrowDown"),
                contentAfter: unformat(`
                    <table>
                        <tbody>
                            <tr>
                                <td><br></td>
                                <td><br></td>
                            </tr>
                            <tr>
                                <td><br></td>
                                <td><br></td>
                            </tr>
                        </tbody>
                    </table>
                    <table>
                        <tbody>
                            <tr>
                                <td>[]<br></td>
                                <td><br></td>
                            </tr>
                            <tr>
                                <td><br></td>
                                <td><br></td>
                            </tr>
                        </tbody>
                    </table>
                `),
            });
        });
    });
});

describe("symmetrical selection", () => {
    test("select cells symmetrically when pressing shift + arrow key", async () => {
        const { el } = await setupEditor(
            unformat(
                `<table class="table table-bordered o_table">
                    <tbody>
                        <tr><td>[]<br></td><td><br></td><td><br></td></tr>
                        <tr><td><br></td><td><br></td><td><br></td></tr>
                    </tbody>
                </table>`
            )
        );

        press(["Shift", "ArrowRight"]);
        await animationFrame();

        // Select single empty cell
        expectContentToBe(
            el,
            `<table class="table table-bordered o_table o_selected_table">
                <tbody>
                    <tr><td class="o_selected_td">[]<br></td><td><br></td><td><br></td></tr>
                    <tr><td><br></td><td><br></td><td><br></td></tr>
                </tbody>
            </table>`
        );

        press(["Shift", "ArrowRight"]);
        await animationFrame();

        // Select two cells consecutively
        expectContentToBe(
            el,
            `<table class="table table-bordered o_table o_selected_table">
                <tbody>
                    <tr><td class="o_selected_td">[<br></td><td class="o_selected_td">]<br></td><td><br></td></tr>
                    <tr><td><br></td><td><br></td><td><br></td></tr>
                </tbody>
            </table>`
        );

        press(["Shift", "ArrowDown"]);
        await animationFrame();

        // Extend selection from two cells to four cells
        expectContentToBe(
            el,
            `<table class="table table-bordered o_table o_selected_table">
                <tbody>
                    <tr><td class="o_selected_td">[<br></td><td class="o_selected_td"><br></td><td><br></td></tr>
                    <tr><td class="o_selected_td"><br></td><td class="o_selected_td">]<br></td><td><br></td></tr>
                </tbody>
            </table>`
        );

        press(["Shift", "ArrowLeft"]);
        await animationFrame();

        // Shrink selection from four cells to two cells
        expectContentToBe(
            el,
            `<table class="table table-bordered o_table o_selected_table">
                <tbody>
                    <tr><td class="o_selected_td">[<br></td><td><br></td><td><br></td></tr>
                    <tr><td class="o_selected_td">]<br></td><td><br></td><td><br></td></tr>
                </tbody>
            </table>`
        );

        press(["Shift", "ArrowUp"]);
        await animationFrame();

        // Shrink selection from two cells to single cell
        expectContentToBe(
            el,
            `<table class="table table-bordered o_table o_selected_table">
                <tbody>
                    <tr><td class="o_selected_td">[]<br></td><td><br></td><td><br></td></tr>
                    <tr><td><br></td><td><br></td><td><br></td></tr>
                </tbody>
            </table>`
        );
    });

    test("select single cell containing text when pressing shift + arrow key", async () => {
        const { el, editor } = await setupEditor(
            unformat(
                `<table class="table table-bordered o_table">
                    <tbody>
                        <tr><td>[]<br></td><td><br></td><td><br></td></tr>
                        <tr><td><br></td><td><br></td><td><br></td></tr>
                    </tbody>
                </table>`
            )
        );
        insertText(editor, "ab");
        await animationFrame();

        expectContentToBe(
            el,
            `<table class="table table-bordered o_table">
                <tbody>
                    <tr><td>ab[]<br></td><td><br></td><td><br></td></tr>
                    <tr><td><br></td><td><br></td><td><br></td></tr>
                </tbody>
            </table>`
        );
        const firstTd = el.querySelector("td");
        setSelection({
            anchorNode: firstTd,
            anchorOffset: 0,
            focusNode: firstTd,
            focusOffset: nodeSize(firstTd),
        }); // <td>[ab]</td>

        press(["Shift", "ArrowRight"]);
        await animationFrame();

        expectContentToBe(
            el,
            `<table class="table table-bordered o_table o_selected_table">
                <tbody>
                    <tr><td class="o_selected_td">[ab<br>]</td><td><br></td><td><br></td></tr>
                    <tr><td><br></td><td><br></td><td><br></td></tr>
                </tbody>
            </table>`
        );
    });
});

describe("single cell selection", () => {
    test("should select single empty cell on double click", async () => {
        const { el } = await setupEditor(
            unformat(
                `<table class="table table-bordered o_table">
                    <tbody>
                        <tr><td>[]<br></td><td><br></td><td><br></td></tr>
                        <tr><td><br></td><td><br></td><td><br></td></tr>
                    </tbody>
                </table>`
            )
        );

        const firstTd = el.querySelector("td");
        manuallyDispatchProgrammaticEvent(firstTd, "mousedown", { detail: 2 });
        await animationFrame();

        manuallyDispatchProgrammaticEvent(firstTd, "mouseup", { detail: 2 });
        await animationFrame();

        expectContentToBe(
            el,
            `<table class="table table-bordered o_table o_selected_table">
                <tbody>
                    <tr><td class="o_selected_td">[]<br></td><td><br></td><td><br></td></tr>
                    <tr><td><br></td><td><br></td><td><br></td></tr>
                </tbody>
            </table>`
        );
    });

    test("should select single cell containing text on triple click", async () => {
        const { el } = await setupEditor(
            unformat(
                `<table class="table table-bordered o_table">
                    <tbody>
                        <tr><td>ab[]c<br></td><td><br></td><td><br></td></tr>
                        <tr><td><br></td><td><br></td><td><br></td></tr>
                    </tbody>
                </table>`
            )
        );

        const firstTd = el.querySelector("td");
        manuallyDispatchProgrammaticEvent(firstTd, "mousedown", { detail: 3 });
        await animationFrame();

        manuallyDispatchProgrammaticEvent(firstTd, "mouseup", { detail: 3 });
        await animationFrame();

        expectContentToBe(
            el,
            `<table class="table table-bordered o_table o_selected_table">
                <tbody>
                    <tr><td class="o_selected_td">ab[]c<br></td><td><br></td><td><br></td></tr>
                    <tr><td><br></td><td><br></td><td><br></td></tr>
                </tbody>
            </table>`
        );
    });

    test("should not select single cell containing text on double click", async () => {
        const { el } = await setupEditor(
            unformat(
                `<table class="table table-bordered o_table">
                    <tbody>
                        <tr><td>ab[]c<br></td><td><br></td><td><br></td></tr>
                        <tr><td><br></td><td><br></td><td><br></td></tr>
                    </tbody>
                </table>`
            )
        );

        const firstTd = el.querySelector("td");
        manuallyDispatchProgrammaticEvent(firstTd, "mousedown", { detail: 2 });
        await animationFrame();

        manuallyDispatchProgrammaticEvent(firstTd, "mouseup", { detail: 2 });
        await animationFrame();

        expectContentToBe(
            el,
            `<table class="table table-bordered o_table">
                <tbody>
                    <tr><td>ab[]c<br></td><td><br></td><td><br></td></tr>
                    <tr><td><br></td><td><br></td><td><br></td></tr>
                </tbody>
            </table>`
        );
    });
});

describe("deselecting table", () => {
    test("deselect table using keyboard if it is fully selected", async () => {
        const { el } = await setupEditor(
            unformat(
                `<p>[abc</p>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr><td><br></td><td><br></td><td><br></td></tr>
                        <tr><td><br></td><td><br></td><td>]<br></td></tr>
                    </tbody>
                </table>`
            )
        );

        expectContentToBe(
            el,
            `<p>[abc</p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr><td class="o_selected_td"><br></td><td class="o_selected_td"><br></td><td class="o_selected_td"><br></td></tr>
                        <tr><td class="o_selected_td"><br></td><td class="o_selected_td"><br></td><td class="o_selected_td">]<br></td></tr>
                    </tbody>
                </table>`
        );

        press(["Shift", "ArrowUp"]);
        await animationFrame();

        expectContentToBe(
            el,
            `<p>[abc]</p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr><td><br></td><td><br></td><td><br></td></tr>
                    <tr><td><br></td><td><br></td><td><br></td></tr>
                </tbody>
            </table>`
        );
    });
});
