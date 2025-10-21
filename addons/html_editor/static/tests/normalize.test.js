import { test } from "@odoo/hoot";
import { testEditor } from "./_helpers/editor";
import { unformat } from "./_helpers/format";

test("should remove empty class attribute", async () => {
    // content after is compared after cleaning up DOM
    await testEditor({
        contentBefore: '<div class=""></div>',
        contentAfter: "<div><br></div>",
    });
});

test("should remove `style.color` from table and apply it to tds", async () => {
    await testEditor({
        contentBefore: unformat(`
                <table style="color: red;" class="o_selected_table"><tbody>
                    <tr><td class="o_selected_td">ab</td></tr>
                    <tr><td>ab</td></tr>
                </tbody></table>
            `),
        contentBeforeEdit: unformat(`
            <p data-selection-placeholder=""><br></p>
            <table style="" class="o_selected_table">
                <tbody>
                    <tr><td class="o_selected_td" style="color: red;">ab</td></tr>
                    <tr><td style="color: red;">ab</td></tr>
                </tbody>
            </table>
            <p data-selection-placeholder=""><br></p>
        `),
    });
});

test("should remove `style.color` from table and apply it to td without `style.color`", async () => {
    await testEditor({
        contentBefore: unformat(`
                <table style="color: red;"><tbody>
                    <tr><td>ab</td></tr>
                    <tr><td style="color: green;">ab</td></tr>
                </tbody></table>
            `),
        contentBeforeEdit: unformat(`
            <p data-selection-placeholder=""><br></p>
            <table style="">
                <tbody>
                    <tr><td style="color: red;">ab</td></tr>
                    <tr><td style="color: green;">ab</td></tr>
                </tbody>
            </table>
            <p data-selection-placeholder=""><br></p>
        `),
    });
});
