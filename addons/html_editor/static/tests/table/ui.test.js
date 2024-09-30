import { expect, test } from "@odoo/hoot";
import { click, hover, queryAllAttributes, queryOne, waitFor, waitForNone } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { setupEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { getContent } from "../_helpers/selection";
import { undo } from "../_helpers/user_actions";

function availableCommands(menu) {
    return queryAllAttributes("span div.user-select-none", "name", { root: menu });
}

test("should only display the table ui menu if the table isContentEditable=true", async () => {
    const { el } = await setupEditor(`
        <table><tbody><tr>
            <td>11[]</td>
        </tr></tbody></table>`);
    expect(".o-we-table-menu").toHaveCount(0);

    await hover(el.querySelector("td"));
    await waitFor(".o-we-table-menu");
    // 1 menu for columns, and 1 for rows
    expect(".o-we-table-menu").toHaveCount(2);
});

test("should display the table ui menu only if hover on first row/col", async () => {
    const { el } = await setupEditor(`
        <table>
            <tbody>
            <tr><td class="a">1[]</td><td class="b">2</td></tr>
            <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>`);
    expect(".o-we-table-menu").toHaveCount(0);

    await hover(el.querySelector("td.a"));
    await waitFor(".o-we-table-menu");
    expect("[data-type='column'].o-we-table-menu").toHaveCount(1);
    expect("[data-type='row'].o-we-table-menu").toHaveCount(1);

    await hover(el.querySelector("td.b"));
    await waitForNone("[data-type='row'].o-we-table-menu");
    expect("[data-type='column'].o-we-table-menu").toHaveCount(1);

    await hover(el.querySelector("td.c"));
    await waitForNone("[data-type='column'].o-we-table-menu");
    expect("[data-type='row'].o-we-table-menu").toHaveCount(1);

    await hover(el.querySelector("td.d"));
    await waitForNone(".o-we-table-menu");
});

test("should not display the table ui menu if the table element isContentEditable=false", async () => {
    const { el } = await setupEditor(`
        <table contenteditable="false"><tbody><tr>
            <td>11[]</td>
        </tr></tbody></table>`);
    expect(".o-we-table-menu").toHaveCount(0);

    await hover(el.querySelector("td"));
    await animationFrame();
    expect(".o-we-table-menu").toHaveCount(0);
});

test("should not display the table ui menu if we leave the editor content", async () => {
    const { el } = await setupEditor(`
        <table><tbody><tr>
            <td>11[]</td>
        </tr></tbody></table>`);
    expect(".o-we-table-menu").toHaveCount(0);

    await hover(el.querySelector("td"));
    await animationFrame();
    expect(".o-we-table-menu").toHaveCount(2);

    await hover(el.parentElement);
    await animationFrame();
    expect(".o-we-table-menu").toHaveCount(0);
});

test.tags("desktop")(
    "should display the resizeCursor if the table element isContentEditable=true",
    async () => {
        const { el } = await setupEditor(`
        <table><tbody><tr>
            <td>11[]</td>
        </tr></tbody></table>`);

        expect(".o_col_resize").toHaveCount(0);
        expect(".o_row_resize").toHaveCount(0);

        const td = el.querySelector("td");
        const tdBox = td.getBoundingClientRect();
        const x = tdBox.x + 1;
        const y = tdBox.bottom - tdBox.height / 2;

        await hover(td, { position: { x, y } });

        await waitFor(".o_col_resize");
        expect(".o_col_resize").toHaveCount(1);
    }
);

test("should not display the resizeCursor if the table element isContentEditable=false", async () => {
    const { el } = await setupEditor(`
        <table contenteditable="false"><tbody><tr>
            <td>11[]</td>
        </tr></tbody></table>`);

    expect(".o_col_resize").toHaveCount(0);
    expect(".o_row_resize").toHaveCount(0);

    await hover(el.querySelector("td"));

    await animationFrame();
    expect(".o_col_resize").toHaveCount(0);
});

test("list of table commands in first column", async () => {
    const { el } = await setupEditor(`
        <p><br></p>
        <table>
            <tbody>
            <tr><td class="a">1[]</td><td class="b">2</td><td class="c">3</td></tr>
            </tbody>
        </table>`);
    expect(".o-we-table-menu").toHaveCount(0);

    // check list of commands on first column
    await hover(el.querySelector("td.a"));
    await waitFor(".o-we-table-menu");
    expect("[data-type='column'].o-we-table-menu").toHaveCount(1);
    expect("[data-type='row'].o-we-table-menu").toHaveCount(1);
    await click("[data-type='column'].o-we-table-menu");
    await waitFor(".dropdown-menu");
    await hover(el);
    await animationFrame();
    expect("[data-type='column'].o-we-table-menu").toHaveCount(1);
    expect("[data-type='row'].o-we-table-menu").toHaveCount(0);
    expect(availableCommands(queryOne(".dropdown-menu"))).toEqual([
        // no move left
        "move_right",
        "insert_left",
        "insert_right",
        "delete",
    ]);
});

test("list of table commands in second column", async () => {
    const { el } = await setupEditor(`
        <table>
            <tbody>
            <tr><td class="a">1[]</td><td class="b">2</td><td class="c">3</td></tr>
            </tbody>
        </table>`);
    expect(".o-we-table-menu").toHaveCount(0);

    // check list of commands on second column
    await hover(el.querySelector("td.b"));
    await waitFor(".o-we-table-menu");
    expect("[data-type='column'].o-we-table-menu").toHaveCount(1);
    await click("[data-type='column'].o-we-table-menu");
    await waitFor(".dropdown-menu");
    expect(availableCommands(queryOne(".dropdown-menu"))).toEqual([
        "move_left",
        "move_right",
        "insert_left",
        "insert_right",
        "delete",
    ]);
});

test("list of table commands in last column", async () => {
    const { el } = await setupEditor(`
        <table>
            <tbody>
            <tr><td class="a">1[]</td><td class="b">2</td><td class="c">3</td></tr>
            </tbody>
        </table>`);
    expect(".o-we-table-menu").toHaveCount(0);

    // check list of commands on last column
    await hover(el.querySelector("td.c"));
    await waitFor(".o-we-table-menu");
    expect("[data-type='column'].o-we-table-menu").toHaveCount(1);
    await click("[data-type='column'].o-we-table-menu");
    await waitFor(".dropdown-menu");
    expect(availableCommands(queryOne(".dropdown-menu"))).toEqual([
        "move_left",
        // no move right
        "insert_left",
        "insert_right",
        "delete",
    ]);
});

test("list of table commands in first row", async () => {
    const { el } = await setupEditor(`
        <table>
            <tbody>
            <tr><td class="a">1[]</td></tr>
            <tr><td class="b">2</td></tr>
            <tr><td class="c">3</td></tr>
            </tbody>
        </table>`);
    expect(".o-we-table-menu").toHaveCount(0);

    // check list of commands on first row
    await hover(el.querySelector("td.a"));
    await waitFor(".o-we-table-menu");
    expect("[data-type='column'].o-we-table-menu").toHaveCount(1);
    expect("[data-type='row'].o-we-table-menu").toHaveCount(1);
    await click("[data-type='row'].o-we-table-menu");
    await waitFor(".dropdown-menu");
    await hover(el);
    await animationFrame();
    expect("[data-type='column'].o-we-table-menu").toHaveCount(0);
    expect("[data-type='row'].o-we-table-menu").toHaveCount(1);
    expect(availableCommands(queryOne(".dropdown-menu"))).toEqual([
        // no move up
        "move_down",
        "insert_above",
        "insert_below",
        "delete",
    ]);
});

test("list of table commands in second row", async () => {
    const { el } = await setupEditor(`
        <table>
            <tbody>
            <tr><td class="a">1[]</td></tr>
            <tr><td class="b">2</td></tr>
            <tr><td class="c">3</td></tr>
            </tbody>
        </table>`);
    expect(".o-we-table-menu").toHaveCount(0);

    // check list of commands on second row
    await hover(el.querySelector("td.b"));
    await waitFor(".o-we-table-menu");
    expect("[data-type='row'].o-we-table-menu").toHaveCount(1);
    await click("[data-type='row'].o-we-table-menu");
    await waitFor(".dropdown-menu");
    expect(availableCommands(queryOne(".dropdown-menu"))).toEqual([
        "move_up",
        "move_down",
        "insert_above",
        "insert_below",
        "delete",
    ]);
});

test("list of table commands in last row", async () => {
    const { el } = await setupEditor(`
        <table>
            <tbody>
            <tr><td class="a">1[]</td></tr>
            <tr><td class="b">2</td></tr>
            <tr><td class="c">3</td></tr>
            </tbody>
        </table>`);
    expect(".o-we-table-menu").toHaveCount(0);

    // check list of commands on last row
    await hover(el.querySelector("td.c"));
    await waitFor(".o-we-table-menu");
    expect("[data-type='row'].o-we-table-menu").toHaveCount(1);
    await click("[data-type='row'].o-we-table-menu");
    await waitFor(".dropdown-menu");
    expect(availableCommands(queryOne(".dropdown-menu"))).toEqual([
        "move_up",
        // no move down
        "insert_above",
        "insert_below",
        "delete",
    ]);
});

test("open/close table menu", async () => {
    const { el } = await setupEditor(`
        <table>
            <tbody>
            <tr><td class="a">1[]</td></tr>
            <tr><td class="b">2</td></tr>
            <tr><td class="c">3</td></tr>
            </tbody>
        </table>`);
    expect(".o-we-table-menu").toHaveCount(0);

    // check list of commands on first row
    await hover(el.querySelector("td.a"));
    await waitFor(".o-we-table-menu");
    expect("[data-type='column'].o-we-table-menu").toHaveCount(1);
    expect("[data-type='row'].o-we-table-menu").toHaveCount(1);

    await click("[data-type='row'].o-we-table-menu");
    await waitFor(".dropdown-menu");
    await click("[data-type='row'].o-we-table-menu");
    await animationFrame();
    expect("[data-type='column'].o-we-table-menu").toHaveCount(0);
    expect("[data-type='row'].o-we-table-menu").toHaveCount(1);
    expect(".dropdown-menu").toHaveCount(0);

    await hover(el);
    await animationFrame();
    expect("[data-type='column'].o-we-table-menu").toHaveCount(0);
    expect("[data-type='row'].o-we-table-menu").toHaveCount(0);
    expect(".dropdown-menu").toHaveCount(0);
});

test("basic delete column operation", async () => {
    const { el, editor } = await setupEditor(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td class="b">2</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>`)
    );
    expect(".o-we-table-menu").toHaveCount(0);

    // hover on td to show col ui
    await hover(el.querySelector("td.b"));
    await waitFor(".o-we-table-menu");

    // click on it to open dropdown
    await click(".o-we-table-menu");
    await waitFor("div[name='delete']");

    // delete column
    await click("div[name='delete']");
    // not sure about selection...
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">[]1</td></tr>
                <tr><td class="c">3</td></tr>
            </tbody>
        </table>`)
    );

    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td class="b">2</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>`)
    );
});

test("basic delete row operation", async () => {
    const { el, editor } = await setupEditor(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td class="b">2</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>`)
    );
    expect(".o-we-table-menu").toHaveCount(0);

    // hover on td to show col ui
    await hover(el.querySelector("td.c"));
    await waitFor(".o-we-table-menu");

    // click on it to open dropdown
    await click(".o-we-table-menu");
    await waitFor("div[name='delete']");

    // delete row
    await click("div[name='delete']");
    // not sure about selection...
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">[]1</td><td class="b">2</td></tr>
            </tbody>
        </table>`)
    );

    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td class="b">2</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>`)
    );
});

test("insert column left operation", async () => {
    const { el, editor } = await setupEditor(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td class="b">2</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>`)
    );
    expect(".o-we-table-menu").toHaveCount(0);

    // hover on td to show col ui
    await hover(el.querySelector("td.b"));
    await waitFor(".o-we-table-menu");

    // click on it to open dropdown
    await click(".o-we-table-menu");
    await waitFor("div[name='insert_left']");

    // insert column left
    await click("div[name='insert_left']");
    expect(getContent(el)).toBe(
        unformat(`
        <table style="width: 20px;">
            <tbody>
                <tr>
                    <td class="a" style="width: 13px;">1[]</td>
                    <td style="width: 13px;"><p><br></p></td>
                    <td class="b" style="width: 13px;">2</td>
                </tr>
                <tr>
                    <td class="c">3</td>
                    <td><p><br></p></td>
                    <td class="d">4</td>
                </tr>
            </tbody>
        </table>`)
    );

    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td class="b">2</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>`)
    );
});

test("insert column right operation", async () => {
    const { el, editor } = await setupEditor(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td class="b">2</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>`)
    );
    expect(".o-we-table-menu").toHaveCount(0);

    // hover on td to show col ui
    await hover(el.querySelector("td.a"));
    await waitFor("[data-type='column'].o-we-table-menu");

    // click on it to open dropdown
    await click("[data-type='column'].o-we-table-menu");
    await waitFor("div[name='insert_right']");

    // insert column right
    await click("div[name='insert_right']");
    expect(getContent(el)).toBe(
        unformat(`
        <table style="width: 20px;">
            <tbody>
                <tr>
                    <td class="a" style="width: 13px;">1[]</td>
                    <td style="width: 13px;"><p><br></p></td>
                    <td class="b" style="width: 13px;">2</td>
                </tr>
                <tr>
                    <td class="c">3</td>
                    <td><p><br></p></td>
                    <td class="d">4</td>
                </tr>
            </tbody>
        </table>`)
    );

    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td class="b">2</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>`)
    );
});

test("insert row above operation", async () => {
    const { el, editor } = await setupEditor(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td class="b">2</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>`)
    );
    expect(".o-we-table-menu").toHaveCount(0);

    // hover on td to show row ui
    await hover(el.querySelector("td.c"));
    await waitFor(".o-we-table-menu");

    // click on it to open dropdown
    await click(".o-we-table-menu");
    await waitFor("div[name='insert_above']");

    // insert row above
    await click("div[name='insert_above']");
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
                <tr>
                    <td class="a">1[]</td>
                    <td class="b">2</td>
                </tr>
                <tr style="height: 23px;">
                    <td><p><br></p></td>
                    <td><p><br></p></td>
                </tr>
                <tr>
                    <td class="c">3</td>
                    <td class="d">4</td>
                </tr>
            </tbody>
        </table>`)
    );

    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td class="b">2</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>`)
    );
});

test("insert row below operation", async () => {
    const { el, editor } = await setupEditor(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td class="b">2</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>`)
    );
    expect(".o-we-table-menu").toHaveCount(0);

    // hover on td to show row ui
    await hover(el.querySelector("td.a"));
    await waitFor("[data-type='row'].o-we-table-menu");

    // click on it to open dropdown
    await click("[data-type='row'].o-we-table-menu");
    await waitFor("div[name='insert_below']");

    // insert row below
    await click("div[name='insert_below']");
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
                <tr>
                    <td class="a">1[]</td>
                    <td class="b">2</td>
                </tr>
                <tr style="height: 23px;">
                    <td><p><br></p></td>
                    <td><p><br></p></td>
                </tr>
                <tr>
                    <td class="c">3</td>
                    <td class="d">4</td>
                </tr>
            </tbody>
        </table>`)
    );

    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td class="b">2</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>`)
    );
});

test("move column left operation", async () => {
    const { el, editor } = await setupEditor(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">1</td><td class="b">2[]</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>`)
    );
    expect(".o-we-table-menu").toHaveCount(0);

    // hover on td to show row ui
    await hover(el.querySelector("td.b"));
    await waitFor("[data-type='column'].o-we-table-menu");

    // click on it to open dropdown
    await click("[data-type='column'].o-we-table-menu");
    await waitFor("div[name='move_left']");

    // move column left
    await click("div[name='move_left']");
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
            <tr><td class="b">2[]</td><td class="a">1</td></tr>
            <tr><td class="d">4</td><td class="c">3</td></tr>
            </tbody>
        </table>`)
    );

    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">1</td><td class="b">2[]</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>`)
    );
});

test("move column right operation", async () => {
    const { el, editor } = await setupEditor(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">1</td><td class="b">2[]</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>`)
    );
    expect(".o-we-table-menu").toHaveCount(0);

    // hover on td to show row ui
    await hover(el.querySelector("td.a"));
    await waitFor("[data-type='column'].o-we-table-menu");

    // click on it to open dropdown
    await click("[data-type='column'].o-we-table-menu");
    await waitFor("div[name='move_right']");

    // move column right
    await click("div[name='move_right']");
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
            <tr><td class="b">2[]</td><td class="a">1</td></tr>
            <tr><td class="d">4</td><td class="c">3</td></tr>
            </tbody>
        </table>`)
    );

    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">1</td><td class="b">2[]</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>`)
    );
});

test("move row above operation", async () => {
    const { el, editor } = await setupEditor(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td class="b">2</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>`)
    );
    expect(".o-we-table-menu").toHaveCount(0);

    // hover on td to show row ui
    await hover(el.querySelector("td.c"));
    await waitFor("[data-type='row'].o-we-table-menu");

    // click on it to open dropdown
    await click("[data-type='row'].o-we-table-menu");
    await waitFor("div[name='move_up']");

    // move row up
    await click("div[name='move_up']");
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
            <tr><td class="c">3</td><td class="d">4</td></tr>
            <tr><td class="a">1[]</td><td class="b">2</td></tr>
            </tbody>
        </table>`)
    );

    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td class="b">2</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>`)
    );
});

test("preserve table rows width on move row above operation", async () => {
    const { el } = await setupEditor(
        unformat(`
        <table>
            <tbody>
                <tr><td style="width: 100px;" class="a">1[]</td><td style="width: 200px;" class="b">2</td></tr>
                <tr><td style="width: 150px;" class="c">3</td><td style="width: 150px;" class="d">4</td></tr>
                <tr><td style="width: 150px;" class="e">5</td><td style="width: 150px;" class="f">6</td></tr>
            </tbody>
        </table>`)
    );
    expect(".o-we-table-menu").toHaveCount(0);

    // hover on td to show row ui
    await hover(el.querySelector("td.c"));
    await waitFor("[data-type='row'].o-we-table-menu");

    // click on it to open dropdown
    await click("[data-type='row'].o-we-table-menu");
    await waitFor("div[name='move_up']");

    // move row up
    await click("div[name='move_up']");
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
                <tr><td style="width: 100px;" class="c">3</td><td style="width: 200px;" class="d">4</td></tr>
                <tr><td style="width: 100px;" class="a">1[]</td><td style="width: 200px;" class="b">2</td></tr>
                <tr><td style="width: 150px;" class="e">5</td><td style="width: 150px;" class="f">6</td></tr>
            </tbody>
        </table>`)
    );
});

test("move row below operation", async () => {
    const { el, editor } = await setupEditor(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td class="b">2</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>`)
    );
    expect(".o-we-table-menu").toHaveCount(0);

    // hover on td to show row ui
    await hover(el.querySelector("td.a"));
    await waitFor("[data-type='row'].o-we-table-menu");

    // click on it to open dropdown
    await click("[data-type='row'].o-we-table-menu");
    await waitFor("div[name='move_down']");

    // move row below
    await click("div[name='move_down']");
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
            <tr><td class="c">3</td><td class="d">4</td></tr>
            <tr><td class="a">1[]</td><td class="b">2</td></tr>
            </tbody>
        </table>`)
    );

    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td class="b">2</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>`)
    );
});

test("preserve table rows width on move row below operation", async () => {
    const { el } = await setupEditor(
        unformat(`
        <table>
            <tbody>
                <tr><td style="width: 100px;" class="a">1[]</td><td style="width: 200px;" class="b">2</td></tr>
                <tr><td style="width: 150px;" class="c">3</td><td style="width: 150px;" class="d">4</td></tr>
                <tr><td style="width: 150px;" class="e">5</td><td style="width: 150px;" class="f">6</td></tr>
            </tbody>
        </table>`)
    );
    expect(".o-we-table-menu").toHaveCount(0);

    // hover on td to show row ui
    await hover(el.querySelector("td.a"));
    await waitFor("[data-type='row'].o-we-table-menu");

    // click on it to open dropdown
    await click("[data-type='row'].o-we-table-menu");
    await waitFor("div[name='move_down']");

    // move row below
    await click("div[name='move_down']");
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
                <tr><td style="width: 100px;" class="c">3</td><td style="width: 200px;" class="d">4</td></tr>
                <tr><td style="width: 100px;" class="a">1[]</td><td style="width: 200px;" class="b">2</td></tr>
                <tr><td style="width: 150px;" class="e">5</td><td style="width: 150px;" class="f">6</td></tr>
            </tbody>
        </table>`)
    );
});

test("reset table size to remove custom width", async () => {
    const { el, editor } = await setupEditor(
        unformat(`
        <table style="width: 150px;">
            <tbody>
            <tr><td style="width: 100px;" class="a">1[]</td></tr>
            <tr><td style="width: 50px;" class="b">2</td></tr>
            </tbody>
        </table>`)
    );
    expect(".o-we-table-menu").toHaveCount(0);

    await hover(el.querySelector("td.a"));
    await waitFor(".o-we-table-menu");
    expect("[data-type='row'].o-we-table-menu").toHaveCount(1);

    await click("[data-type='row'].o-we-table-menu");
    await waitFor(".dropdown-menu");
    await click(queryOne(".dropdown-menu [name='reset_size']"));
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
                <tr><td style="" class="a">1[]</td></tr>
                <tr><td style="" class="b">2</td></tr>
            </tbody>
        </table>`)
    );

    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
        <table style="width: 150px;">
            <tbody>
            <tr><td style="width: 100px;" class="a">1[]</td></tr>
            <tr><td style="width: 50px;" class="b">2</td></tr>
            </tbody>
        </table>`)
    );
});

test("reset table size to remove custom height", async () => {
    const { el, editor } = await setupEditor(
        unformat(`
        <table>
            <tbody>
            <tr style="height: 100px;"><td class="a">1[]</td></tr>
            <tr style="height: 50px;"><td class="b">2</td></tr>
            </tbody>
        </table>`)
    );
    expect(".o-we-table-menu").toHaveCount(0);

    await hover(el.querySelector("td.a"));
    await waitFor(".o-we-table-menu");
    expect("[data-type='row'].o-we-table-menu").toHaveCount(1);

    await click("[data-type='row'].o-we-table-menu");
    await waitFor(".dropdown-menu");
    await click(queryOne(".dropdown-menu [name='reset_size']"));
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
                <tr style=""><td class="a">1[]</td></tr>
                <tr style=""><td class="b">2</td></tr>
            </tbody>
        </table>`)
    );

    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
            <tr style="height: 100px;"><td class="a">1[]</td></tr>
            <tr style="height: 50px;"><td class="b">2</td></tr>
            </tbody>
        </table>`)
    );
});
