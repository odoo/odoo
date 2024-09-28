import { expect, test } from "@odoo/hoot";
import { setupEditor } from "../_helpers/editor";
import { click, queryAll, queryFirst, waitFor } from "@odoo/hoot-dom";
import { animationFrame, tick } from "@odoo/hoot-mock";
import { setSelection } from "../_helpers/selection";

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
    await click(".o-select-color-background");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(1);

    await click(".o_color_button[data-color='#6BADDE']");
    await animationFrame();
    expect(".o-we-toolbar").toHaveCount(1); // toolbar still open
    expect(".o_font_color_selector").toHaveCount(0); // selector closed

    // Collapse selection to deselect cells
    setSelection({ anchorNode: queryFirst("td"), anchorOffset: 0 });
    await tick();

    const cells = queryAll("td");
    expect(cells[0]).toHaveStyle({ "background-color": "rgb(107, 173, 222)" });
    expect(cells[1]).toHaveStyle({ "background-color": "rgb(107, 173, 222)" });
    expect(cells[2]).not.toHaveStyle({ "background-color": "rgb(107, 173, 222)" });
});
