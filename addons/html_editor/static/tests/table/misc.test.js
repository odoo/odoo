import { describe, expect, test } from "@odoo/hoot";
import { setupEditor } from "../_helpers/editor";
import { click, manuallyDispatchProgrammaticEvent, queryAll, queryFirst } from "@odoo/hoot-dom";
import { animationFrame, tick } from "@odoo/hoot-mock";
import { getContent, setSelection } from "../_helpers/selection";
import { execCommand } from "../_helpers/userCommands";
import { expandToolbar } from "../_helpers/toolbar";
import { expectElementCount } from "../_helpers/ui_expectations";
import { deleteBackward } from "../_helpers/user_actions";
import { unformat } from "../_helpers/format";

function insertTable(editor, cols, rows) {
    execCommand(editor, "insertTable", { cols, rows });
}

describe("insertTable", () => {
    test("creates correct rows and columns", async () => {
        const { el, editor } = await setupEditor("<p>hello[]</p>", {});
        insertTable(editor, 4, 3);
        expect(el.querySelectorAll("tr")).toHaveLength(3);
        expect(el.querySelectorAll("td")).toHaveLength(12);
    });

    test("inserts table at the start", async () => {
        const { el, editor } = await setupEditor("<p>[]hello</p>", {});
        insertTable(editor, 1, 1);
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td>
                                <p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>
                            </td>
                        </tr>
                    </tbody>
                </table>
                <p>hello</p>
            `)
        );
    });

    test("inserts table in the middle", async () => {
        const { el, editor } = await setupEditor("<p>he[]llo</p>", {});
        insertTable(editor, 1, 1);
        expect(getContent(el)).toBe(
            unformat(`
                <p>he</p>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td>
                                <p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>
                            </td>
                        </tr>
                    </tbody>
                </table>
                <p>llo</p>
            `)
        );
    });

    test("inserts table at the end", async () => {
        const { el, editor } = await setupEditor("<p>hello[]</p>", {});
        insertTable(editor, 1, 1);
        expect(getContent(el)).toBe(
            unformat(`
                <p>hello</p>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td>
                                <p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>
                            </td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
            `)
        );
    });
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
