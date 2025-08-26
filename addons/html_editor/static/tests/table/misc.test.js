import { expect, test } from "@odoo/hoot";
import { setupEditor } from "../_helpers/editor";
import { click, manuallyDispatchProgrammaticEvent, queryAll, queryFirst } from "@odoo/hoot-dom";
import { animationFrame, tick } from "@odoo/hoot-mock";
import { setSelection } from "../_helpers/selection";
import { execCommand } from "../_helpers/userCommands";
import { expandToolbar } from "../_helpers/toolbar";
import { expectElementCount } from "../_helpers/ui_expectations";
import { deleteBackward } from "../_helpers/user_actions";

function insertTable(editor, cols, rows) {
    execCommand(editor, "insertTable", { cols, rows });
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

    await expandToolbar();
    expect(".o_font_color_selector").toHaveCount(0);
    await click(".o-select-color-background");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(1);

    await click(".o_color_button[data-color='#6BADDE']");
    await animationFrame();
    await expectElementCount(".o-we-toolbar", 1);
    expect(".o_font_color_selector").toHaveCount(0); // selector closed

    // Collapse selection to deselect cells
    setSelection({ anchorNode: queryFirst("td"), anchorOffset: 0 });
    await tick();

    const cells = queryAll("td");
    expect(cells[0]).toHaveStyle({ "background-color": "rgba(107, 173, 222, 0.6)" });
    expect(cells[1]).toHaveStyle({ "background-color": "rgba(107, 173, 222, 0.6)" });
    expect(cells[2]).not.toHaveStyle({ "background-color": "rgba(107, 173, 222, 0.6)" });
});

test("remove text from single selected cell", async () => {
    const { editor } = await setupEditor(`
        <table class="table table-bordered o_table">
            <tbody>
                <tr>
                    <td><p>[]abc</p></td>
                    <td><p><br></p></td>
                    <td><p><br></p></td>
                </tr>
            </tbody>
        </table>`);

    const firstP = queryFirst("td p");
    const { left, top } = firstP.getBoundingClientRect();
    manuallyDispatchProgrammaticEvent(firstP, "mousedown", {
        detail: 3,
        clientX: left,
        clientY: top,
    });
    await animationFrame();

    manuallyDispatchProgrammaticEvent(firstP, "mouseup", {
        detail: 3,
        clientX: left,
        clientY: top,
    });
    await animationFrame();
    deleteBackward(editor);

    expect(queryFirst("td p")).toHaveOuterHTML("<p><br></p>");
});
