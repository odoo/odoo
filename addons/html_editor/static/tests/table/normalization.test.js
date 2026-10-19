import { describe, test } from "@odoo/hoot";
import { testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";

describe("column width normalization", () => {
    test("should leave the table unchanged when no cell widths are present", async () => {
        await testEditor({
            contentBefore: unformat(`
                <table>
                    <tbody>
                        <tr>
                            <td>A</td>
                            <td>B</td>
                        </tr>
                    </tbody>
                </table>
            `),
            contentAfter: unformat(`
                <table>
                    <tbody>
                        <tr>
                            <td>A</td>
                            <td>B</td>
                        </tr>
                    </tbody>
                </table>
            `),
        });
    });

    test("should create a colgroup from cell widths when no colspan is present", async () => {
        await testEditor({
            contentBefore: unformat(`
                <table>
                    <tbody>
                        <tr>
                            <td style="width: 100px;">A</td>
                            <td style="width: 200px;">B</td>
                        </tr>
                    </tbody>
                </table>
            `),
            contentAfter: unformat(`
                <table>
                    <colgroup>
                        <col style="width: 100px;">
                        <col style="width: 200px;">
                    </colgroup>
                    <tbody>
                        <tr>
                            <td>A</td>
                            <td>B</td>
                        </tr>
                    </tbody>
                </table>
            `),
        });
    });

    test("should create empty cols for cells without explicit widths", async () => {
        await testEditor({
            contentBefore: unformat(`
                <table style="width: 100px;">
                    <tbody>
                        <tr>
                            <td style="width: 20px;">A</td>
                            <td>B</td>
                            <td>C</td>
                        </tr>
                    </tbody>
                </table>
            `),
            contentAfter: unformat(`
                <table style="width: 100px;">
                    <colgroup>
                        <col style="width: 20px;">
                        <col>
                        <col>
                    </colgroup>
                    <tbody>
                        <tr>
                            <td>A</td>
                            <td>B</td>
                            <td>C</td>
                        </tr>
                    </tbody>
                </table>
            `),
        });
    });

    test("should create missing cols when an existing colgroup is shorter than a row without colspan", async () => {
        await testEditor({
            contentBefore: unformat(`
                <table>
                    <colgroup>
                        <col style="width: 100px;">
                    </colgroup>
                    <tbody>
                        <tr>
                            <td>A</td>
                            <td style="width: 200px;">B</td>
                        </tr>
                    </tbody>
                </table>
            `),
            contentAfter: unformat(`
                <table>
                    <colgroup>
                        <col style="width: 100px;">
                        <col style="width: 200px;">
                    </colgroup>
                    <tbody>
                        <tr>
                            <td>A</td>
                            <td>B</td>
                        </tr>
                    </tbody>
                </table>
            `),
        });
    });

    test("should distribute a colspan cell width evenly across the columns it spans", async () => {
        await testEditor({
            contentBefore: unformat(`
                <table>
                    <tbody>
                        <tr>
                            <td colspan="2" style="width: 200px;">A</td>
                            <td style="width: 50px;">B</td>
                        </tr>
                    </tbody>
                </table>
            `),
            contentAfter: unformat(`
                <table>
                    <colgroup>
                        <col style="width: 100px;">
                        <col style="width: 100px;">
                        <col style="width: 50px;">
                    </colgroup>
                    <tbody>
                        <tr>
                            <td colspan="2">A</td>
                            <td>B</td>
                        </tr>
                    </tbody>
                </table>
            `),
        });
    });

    test("should distribute the leftover width across unresolved columns in a span", async () => {
        await testEditor({
            contentBefore: unformat(`
                <table>
                    <colgroup>
                        <col style="width: 60px;">
                    </colgroup>
                    <tbody>
                        <tr>
                            <td colspan="3" style="width: 300px;">A</td>
                            <td style="width: 80px;">B</td>
                        </tr>
                    </tbody>
                </table>
            `),
            contentAfter: unformat(`
                <table>
                    <colgroup>
                        <col style="width: 60px;">
                        <col style="width: 120px;">
                        <col style="width: 120px;">
                        <col style="width: 80px;">
                    </colgroup>
                    <tbody>
                        <tr>
                            <td colspan="3">A</td>
                            <td>B</td>
                        </tr>
                    </tbody>
                </table>
            `),
        });
    });

    test("should preserve existing col widths when they differ from the cell width", async () => {
        await testEditor({
            contentBefore: unformat(`
                <table>
                    <colgroup>
                        <col style="width: 150px;">
                        <col style="width: 150px;">
                        <col style="width: 60px;">
                    </colgroup>
                    <tbody>
                        <tr>
                            <td style="width: 200px;">A</td>
                            <td style="width: 200px;">B</td>
                            <td style="width: 60px;">C</td>
                        </tr>
                    </tbody>
                </table>
            `),
            contentAfter: unformat(`
                <table>
                    <colgroup>
                        <col style="width: 150px;">
                        <col style="width: 150px;">
                        <col style="width: 60px;">
                    </colgroup>
                    <tbody>
                        <tr>
                            <td>A</td>
                            <td>B</td>
                            <td>C</td>
                        </tr>
                    </tbody>
                </table>
            `),
        });
    });

    test("should distribute the leftover width across unresolved columns in a span, even when the resolved column isn't first", async () => {
        await testEditor({
            contentBefore: unformat(`
                <table>
                    <colgroup>
                        <col>
                        <col style="width: 60px;">
                    </colgroup>
                    <tbody>
                        <tr>
                            <td colspan="2" style="width: 300px;">A</td>
                            <td style="width: 80px;">B</td>
                        </tr>
                    </tbody>
                </table>
            `),
            contentAfter: unformat(`
                <table>
                    <colgroup>
                        <col style="width: 240px;">
                        <col style="width: 60px;">
                        <col style="width: 80px;">
                    </colgroup>
                    <tbody>
                        <tr>
                            <td colspan="2">A</td>
                            <td>B</td>
                        </tr>
                    </tbody>
                </table>
            `),
        });
    });
});
