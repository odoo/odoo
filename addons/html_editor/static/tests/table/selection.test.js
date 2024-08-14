import { describe, expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { bold, resetSize, setColor } from "../_helpers/user_actions";
import { getContent } from "../_helpers/selection";
import { queryAll } from "@odoo/hoot-dom";

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
                    '<td class="o_selected_td">a]b</td>' +
                    '<td class="o_selected_td">cd</td>' +
                    '<td class="o_selected_td">ef</td>' +
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
                    '<td class="o_selected_td">a]b</td>' +
                    '<td class="o_selected_td">cd</td>' +
                    '<td class="o_selected_td">ef</td></tr></tbody></table>',
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
                                    <font style="color: aquamarine;">a]b</font>
                                </td>
                                <td class="o_selected_td">
                                    <font style="color: aquamarine;">cd</font>
                                </td>
                                <td class="o_selected_td">
                                    <font style="color: aquamarine;">ef</font>
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
                                <font style="color: aquamarine;">a]b</font>
                            </td>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">cd</font>
                            </td>
                            <td class="o_selected_td">
                                <font style="color: aquamarine;">ef</font>
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
