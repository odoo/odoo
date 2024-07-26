import { expect, test } from "@odoo/hoot";
import { setupEditor } from "../_helpers/editor";
import { click, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

function insertTable(editor, cols, rows) {
    editor.dispatch("INSERT_TABLE", { cols, rows });
}

test("can insert a table", async () => {
    const { el, editor } = await setupEditor("<p>hello[]</p>", {});
    insertTable(editor, 4, 3);
    expect(el.querySelectorAll("tr").length).toBe(3);
    expect(el.querySelectorAll("td").length).toBe(12);
});

test("can color cells", async () => {
    await setupEditor(`
        <table>
            <tbody>
                <tr>
                    <td>[ab</td>
                    <td>c]</td>
                    <td>ef</td>
                </tr>
            </tbody>
        </table>`);

    await waitFor(".o-we-toolbar");
    expect(".o_font_color_selector").toHaveCount(0);
    click(".o-select-color-background");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(1);

    click(".o_color_button[data-color='#6BADDE']");
    await animationFrame();
    expect(".o-we-toolbar").toHaveCount(1); // toolbar still open
    expect(".o_font_color_selector").toHaveCount(0); // selector closed
    expect("td.o_selected_td").toHaveStyle({ "background-color": "rgb(107, 173, 222)" });
});
