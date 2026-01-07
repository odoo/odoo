import { describe, expect, test } from "@odoo/hoot";
import {
    click,
    hover,
    queryAll,
    queryAllAttributes,
    queryOne,
    waitFor,
    waitForNone,
} from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { setupEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { getContent } from "../_helpers/selection";
import { undo } from "../_helpers/user_actions";
import { expectElementCount } from "../_helpers/ui_expectations";

function availableCommands(menu) {
    return queryAllAttributes("span div.user-select-none", "name", { root: menu });
}

test("should only display the table ui menu if the table isContentEditable=true", async () => {
    const { el } = await setupEditor(`
        <table><tbody><tr>
            <td>11[]</td>
        </tr></tbody></table>`);
    await expectElementCount(".o-we-table-menu", 0);

    await hover(el.querySelector("td"));
    // 1 menu for columns, and 1 for rows
    await expectElementCount(".o-we-table-menu", 2);
});

test("should display the table ui menu only if hover on first row/col", async () => {
    const { el } = await setupEditor(`
        <table>
            <tbody>
            <tr><td class="a">1[]</td><td class="b">2</td></tr>
            <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>`);
    await expectElementCount(".o-we-table-menu", 0);

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

test("should not display the table UI menu when hovering over non-first row/col cells", async () => {
    const { el } = await setupEditor(`
        <table>
            <tbody>
                <tr><td rowspan="3">1</td><td>2</td><td>3</td></tr>
                <tr><td class="a">4[]</td><td>5</td></tr>
                <tr><td class="b">6</td><td>7</td></tr>
            </tbody>
        </table>`);
    await expectElementCount(".o-we-table-menu", 0);

    await hover(el.querySelector("td.a"));
    await animationFrame();
    await expectElementCount(".o-we-table-menu", 0);

    await hover(el.querySelector("td.b"));
    await animationFrame();
    await expectElementCount(".o-we-table-menu", 0);
});

test("should not display the table ui menu if the table element isContentEditable=false", async () => {
    const { el } = await setupEditor(`
        <table contenteditable="false"><tbody><tr>
            <td>11[]</td>
        </tr></tbody></table>`);
    await expectElementCount(".o-we-table-menu", 0);

    await hover(el.querySelector("td"));
    await animationFrame();
    await expectElementCount(".o-we-table-menu", 0);
});

test("should not display the table ui menu if we leave the editor content", async () => {
    const { el } = await setupEditor(`
        <table><tbody><tr>
            <td>11[]</td>
        </tr></tbody></table>`);
    await expectElementCount(".o-we-table-menu", 0);

    await hover(el.querySelector("td"));
    await animationFrame();
    await expectElementCount(".o-we-table-menu", 2);

    await hover(el.parentElement);
    await animationFrame();
    await expectElementCount(".o-we-table-menu", 0);
});

test("should display the table ui menu when hovering on TH", async () => {
    const { el } = await setupEditor(`
        <table><tbody><tr>
            <th>11[]</th>
        </tr></tbody></table>`);
    await expectElementCount(".o-we-table-menu", 0);

    await hover(el.querySelector("th"));
    await animationFrame();
    await expectElementCount(".o-we-table-menu", 2);
});

test.tags("desktop");
test("should display the resizeCursor if the table element isContentEditable=true", async () => {
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
});

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
    await expectElementCount(".o-we-table-menu", 0);

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
        "clear_content",
    ]);
});

test("list of table commands in second column", async () => {
    const { el } = await setupEditor(`
        <table>
            <tbody>
            <tr><td class="a">1[]</td><td class="b">2</td><td class="c">3</td></tr>
            </tbody>
        </table>`);
    await expectElementCount(".o-we-table-menu", 0);

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
        "clear_content",
    ]);
});

test("list of table commands in last column", async () => {
    const { el } = await setupEditor(`
        <table>
            <tbody>
            <tr><td class="a">1[]</td><td class="b">2</td><td class="c">3</td></tr>
            </tbody>
        </table>`);
    await expectElementCount(".o-we-table-menu", 0);

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
        "clear_content",
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
    await expectElementCount(".o-we-table-menu", 0);

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
        "make_header",
        // no remove header
        // no move up
        "move_down",
        "insert_above",
        "insert_below",
        "toggle_alternating_rows",
        "delete",
        "clear_content",
    ]);
});

test("list of table commands in first row if it's table header (TH)", async () => {
    const { el } = await setupEditor(`
        <table>
            <tbody>
                <tr><th class="a o_table_header">1[]</th></tr>
                <tr><th class="b o_table_header">2</th></tr>
                <tr><th class="c o_table_header">3</th></tr>
            </tbody>
        </table>`);
    await expectElementCount(".o-we-table-menu", 0);

    // check list of commands on table header row
    await hover(el.querySelector("th.a"));
    await waitFor(".o-we-table-menu");
    await expectElementCount("[data-type='column'].o-we-table-menu", 1);
    await expectElementCount("[data-type='row'].o-we-table-menu", 1);
    await click("[data-type='row'].o-we-table-menu");
    await waitFor(".dropdown-menu");
    expect(availableCommands(queryOne(".dropdown-menu"))).toEqual([
        //no make header
        "remove_header",
        // no move up
        "move_down",
        // no insert above
        "insert_below",
        "toggle_alternating_rows",
        "delete",
        "clear_content",
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
    await expectElementCount(".o-we-table-menu", 0);

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
        "toggle_alternating_rows",
        "delete",
        "clear_content",
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
    await expectElementCount(".o-we-table-menu", 0);

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
        "toggle_alternating_rows",
        "delete",
        "clear_content",
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
    await expectElementCount(".o-we-table-menu", 0);

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

test("clear content is hidden in row menu when row has no content", async () => {
    const { el } = await setupEditor(`
        <table>
            <tbody>
                <tr>
                    <td class="a"><p>[]<br></p></td>
                    <td class="b"><p><br></p></td>
                </tr>
                <tr>
                    <td class="c"><p><br></p></td>
                    <td class="d"><p><br></p></td>
                </tr>
            </tbody>
        </table>`);

    await hover(el.querySelector("td.a"));
    await expectElementCount("[data-type='row'].o-we-table-menu", 1);
    await click("[data-type='row'].o-we-table-menu");
    await waitFor(".dropdown-menu");
    expect(availableCommands(queryOne(".dropdown-menu"))).toEqual([
        "make_header",
        "move_down",
        "insert_above",
        "insert_below",
        "toggle_alternating_rows",
        "delete",
        // no clear content
    ]);
});

test("clear content is hidden in column menu when column has no content", async () => {
    const { el } = await setupEditor(`
        <table>
            <tbody>
                <tr>
                    <td class="a"><p>[]<br></p></td>
                    <td class="b"><p><br></p></td>
                </tr>
                <tr>
                    <td class="c"><p><br></p></td>
                    <td class="d"><p><br></p></td>
                </tr>
            </tbody>
        </table>`);

    await hover(el.querySelector("td.a"));
    await expectElementCount("[data-type='row'].o-we-table-menu", 1);
    await click("[data-type='column'].o-we-table-menu");
    await waitFor(".dropdown-menu");
    expect(availableCommands(queryOne(".dropdown-menu"))).toEqual([
        "move_right",
        "insert_left",
        "insert_right",
        "delete",
        // no clear content
    ]);
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
    await expectElementCount(".o-we-table-menu", 0);

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
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr><td class="a">[]1</td></tr>
                <tr><td class="c">3</td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
    );

    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td class="b">2</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
    );
});

test("basic clear column content operation", async () => {
    const { el, editor } = await setupEditor(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a"><p>1[]</p></td><td class="b"><p>2</p></td></tr>
                <tr><td class="c"><p>3</p></td><td class="d"><h1>4</h1></td></tr>
            </tbody>
        </table>`)
    );
    await expectElementCount(".o-we-table-menu", 0);

    // hover on td to show col ui
    await hover(el.querySelector("td.b"));
    await waitFor(".o-we-table-menu");

    // click on it to open dropdown
    await click(".o-we-table-menu");
    await waitFor("div[name='clear_content']");

    // clear content of the column
    await click("div[name='clear_content']");
    // not sure about selection...
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr><td class="a"><p>1[]</p></td><td class="b"><p><br></p></td></tr>
                <tr><td class="c"><p>3</p></td><td class="d"><p><br></p></td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
    );

    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr><td class="a"><p>1[]</p></td><td class="b"><p>2</p></td></tr>
                <tr><td class="c"><p>3</p></td><td class="d"><h1>4</h1></td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
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
    await expectElementCount(".o-we-table-menu", 0);

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
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr><td class="a">[]1</td><td class="b">2</td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
    );

    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td class="b">2</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
    );
});

test("basic clear row content operation", async () => {
    const { el, editor } = await setupEditor(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a"><p>1[]</p></td><td class="b"><p>2</p></td></tr>
                <tr><td class="c"><p>3</p></td><td class="d"><h2>4</h2></td></tr>
            </tbody>
        </table>`)
    );
    await expectElementCount(".o-we-table-menu", 0);

    // hover on td to show col ui
    await hover(el.querySelector("td.c"));
    await waitFor(".o-we-table-menu");

    // click on it to open dropdown
    await click(".o-we-table-menu");
    await waitFor("div[name='clear_content']");

    // clear content of the row
    await click("div[name='clear_content']");
    // not sure about selection...
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr><td class="a"><p>1[]</p></td><td class="b"><p>2</p></td></tr>
                <tr><td class="c"><p><br></p></td><td class="d"><p><br></p></td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
    );

    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr><td class="a"><p>1[]</p></td><td class="b"><p>2</p></td></tr>
                <tr><td class="c"><p>3</p></td><td class="d"><h2>4</h2></td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
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
    await expectElementCount(".o-we-table-menu", 0);

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
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr>
                    <td class="a">1[]</td>
                    <td><p><br></p></td>
                    <td class="b">2</td>
                </tr>
                <tr>
                    <td class="c">3</td>
                    <td><p><br></p></td>
                    <td class="d">4</td>
                </tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
    );

    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td class="b">2</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
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
    await expectElementCount(".o-we-table-menu", 0);

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
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr>
                    <td class="a">1[]</td>
                    <td><p><br></p></td>
                    <td class="b">2</td>
                </tr>
                <tr>
                    <td class="c">3</td>
                    <td><p><br></p></td>
                    <td class="d">4</td>
                </tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
    );

    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td class="b">2</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
    );
});

test("insert column at the start of a merge column", async () => {
    const { el } = await setupEditor(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td>2</td><td>3</td></tr>
                <tr><td colspan="3">4</td></tr>
            </tbody>
        </table>`)
    );
    await expectElementCount(".o-we-table-menu", 0);

    // hover on td to show col ui
    await hover(el.querySelector("td.a"));
    await waitFor("[data-type='column'].o-we-table-menu");

    // click on it to open dropdown
    await click("[data-type='column'].o-we-table-menu");
    await waitFor("div[name='insert_left']");

    // insert column left
    await click("div[name='insert_left']");
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr>
                    <td><p><br></p></td>
                    <td class="a">1[]</td>
                    <td>2</td>
                    <td>3</td>
                </tr>
                <tr>
                    <td><p><br></p></td>
                    <td colspan="3">4</td>
                </tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
    );
});

test("insert column in the middle of a a merged column", async () => {
    const { el } = await setupEditor(
        unformat(`
        <table class="table table-bordered o_table">
            <tbody>
                <tr><td class="a">1[]</td><td>2</td><td>3</td></tr>
                <tr><td colspan="3">4</td></tr>
            </tbody>
        </table>`)
    );
    await expectElementCount(".o-we-table-menu", 0);

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
        <p data-selection-placeholder=""><br></p>
        <table class="table table-bordered o_table">
            <tbody>
                <tr>
                    <td class="a">1[]</td>
                    <td><p><br></p></td>
                    <td>2</td>
                    <td>3</td>
                </tr>
                <tr>
                    <td colspan="4">4</td>
                </tr>
            </tbody>
        </table>
        <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
    );
});

test("insert column at the end of a merged column below", async () => {
    const { el } = await setupEditor(
        unformat(`
        <table class="table table-bordered o_table">
            <tbody>
                <tr><td>1</td><td>2</td><td class="a">3[]</td></tr>
                <tr><td colspan="3">4</td></tr>
            </tbody>
        </table>`)
    );
    await expectElementCount(".o-we-table-menu", 0);

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
        <p data-selection-placeholder=""><br></p>
        <table class="table table-bordered o_table">
            <tbody>
                <tr>
                    <td>1</td>
                    <td>2</td>
                    <td class="a">3[]</td>
                    <td><p><br></p></td>
                </tr>
                <tr>
                    <td colspan="3">4</td>
                    <td><p><br></p></td>
                </tr>
            </tbody>
        </table>
        <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
    );
});

test("insert column right operation when table header exists", async () => {
    const { el } = await setupEditor(
        unformat(`
        <table>
            <tbody>
                <tr><th class="a o_table_header">1[]</th><th class="b o_table_header">2</th></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>`)
    );
    await expectElementCount(".o-we-table-menu", 0);

    // hover on th to show col ui
    await hover(el.querySelector("th.a"));
    await waitFor("[data-type='column'].o-we-table-menu");

    // click on it to open dropdown
    await click("[data-type='column'].o-we-table-menu");
    await waitFor("div[name='insert_right']");

    // insert column right
    await click("div[name='insert_right']");
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr>
                    <th class="a o_table_header">1[]</th>
                    <th class="o_table_header"><p><br></p></th>
                    <th class="b o_table_header">2</th>
                </tr>
                <tr>
                    <td class="c">3</td>
                    <td><p><br></p></td>
                    <td class="d">4</td>
                </tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
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
    await expectElementCount(".o-we-table-menu", 0);

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
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr>
                    <td class="a">1[]</td>
                    <td class="b">2</td>
                </tr>
                <tr>
                    <td><p><br></p></td>
                    <td><p><br></p></td>
                </tr>
                <tr>
                    <td class="c">3</td>
                    <td class="d">4</td>
                </tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
    );

    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td class="b">2</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
    );
});

test("insert row above operation should not retain height and width styles", async () => {
    const { el } = await setupEditor(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td class="b">2</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>`)
    );
    await expectElementCount(".o-we-table-menu", 0);

    // hover on td to show row ui
    await hover(el.querySelector("td.a"));
    await waitFor(".o-we-table-menu");

    // click on it to open dropdown
    await click(".o-we-table-menu");
    await waitFor("div[name='insert_above']");

    // insert row above
    await click("div[name='insert_above']");
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr>
                    <td><p><br></p></td>
                    <td><p><br></p></td>
                </tr>
                <tr>
                    <td class="a">1[]</td>
                    <td class="b">2</td>
                </tr>
                <tr>
                    <td class="c">3</td>
                    <td class="d">4</td>
                </tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
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
    await expectElementCount(".o-we-table-menu", 0);

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
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr>
                    <td class="a">1[]</td>
                    <td class="b">2</td>
                </tr>
                <tr>
                    <td><p><br></p></td>
                    <td><p><br></p></td>
                </tr>
                <tr>
                    <td class="c">3</td>
                    <td class="d">4</td>
                </tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
    );

    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td class="b">2</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
    );
});

test("insert row above the rowspan cell", async () => {
    const { el } = await setupEditor(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a" rowspan="3">1[]</td><td class="b">2</td></tr>
                <tr><td class="c">3</td></tr>
                <tr><td class="d">4</td></tr>
            </tbody>
        </table>`)
    );
    await expectElementCount(".o-we-table-menu", 0);

    // hover on td to show row ui
    await hover(el.querySelector("td.a"));
    await waitFor("[data-type='row'].o-we-table-menu");

    // click on it to open dropdown
    await click("[data-type='row'].o-we-table-menu");
    await waitFor("div[name='insert_above']");

    // insert row above
    await click("div[name='insert_above']");
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr>
                    <td><p><br></p></td>
                    <td><p><br></p></td>
                </tr>
                <tr>
                    <td class="a" rowspan="3">1[]</td>
                    <td class="b">2</td>
                </tr>
                <tr>
                    <td class="c">3</td>
                </tr>
                <tr>
                    <td class="d">4</td>
                </tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
    );
});

test("insert row in the middle of a rowspan cell", async () => {
    const { el } = await setupEditor(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td class="b" rowspan="3">2</td></tr>
                <tr><td class="c">3</td></tr>
                <tr><td class="d">4</td></tr>
            </tbody>
        </table>`)
    );
    await expectElementCount(".o-we-table-menu", 0);

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
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr>
                    <td class="a">1[]</td>
                    <td class="b" rowspan="4">2</td>
                </tr>
                <tr>
                    <td><p><br></p></td>
                </tr>
                <tr>
                    <td class="c">3</td>
                </tr>
                <tr>
                    <td class="d">4</td>
                </tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
    );
});

test("insert row at the end of a rowspan cell", async () => {
    const { el } = await setupEditor(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td class="b" rowspan="3">2</td></tr>
                <tr><td class="c">3</td></tr>
                <tr><td class="d">4</td></tr>
            </tbody>
        </table>`)
    );
    await expectElementCount(".o-we-table-menu", 0);

    // hover on td to show row ui
    await hover(el.querySelector("td.d"));
    await waitFor("[data-type='row'].o-we-table-menu");

    // click on it to open dropdown
    await click("[data-type='row'].o-we-table-menu");
    await waitFor("div[name='insert_below']");

    // insert row below
    await click("div[name='insert_below']");
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr>
                    <td class="a">1[]</td>
                    <td class="b" rowspan="3">2</td>
                </tr>
                <tr>
                    <td class="c">3</td>
                </tr>
                <tr>
                    <td class="d">4</td>
                </tr>
                <tr>
                    <td><p><br></p></td>
                    <td><p><br></p></td>
                </tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
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
    await expectElementCount(".o-we-table-menu", 0);

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
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
            <tr><td class="b">2[]</td><td class="a">1</td></tr>
            <tr><td class="d">4</td><td class="c">3</td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
    );

    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr><td class="a">1</td><td class="b">2[]</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
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
    await expectElementCount(".o-we-table-menu", 0);

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
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
            <tr><td class="b">2[]</td><td class="a">1</td></tr>
            <tr><td class="d">4</td><td class="c">3</td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
    );

    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr><td class="a">1</td><td class="b">2[]</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
    );
});

test("disables move column left/right when current or adjacent columns are affected by colspan", async () => {
    const { el } = await setupEditor(
        unformat(`
        <table class="table table-bordered o_table">
            <tbody>
                <tr>
                    <td><br></td>
                    <td class="a"><br></td>
                    <td class="b"><br></td>
                    <td><br></td>
                    <td class="c"><br></td>
                    <td><br></td>
                </tr>
                <tr>
                    <td><br></td>
                    <td><br></td>
                    <td colspan="2"><br></td>
                    <td><br></td>
                    <td><br></td>
                </tr>
            </tbody>
        </table>`)
    );

    await expectElementCount(".o-we-table-menu", 0);

    // Hover on td.a to show column UI
    await hover(el.querySelector("td.a"));
    await waitFor("[data-type='column'].o-we-table-menu");

    // Open menu and check disabled states
    await click("[data-type='column'].o-we-table-menu");
    await animationFrame();
    expect("div[name='move_right']").toHaveClass("disabled");
    expect("div[name='move_left']").not.toHaveClass("disabled");

    // Close menu
    await click("[data-type='column'].o-we-table-menu");
    await animationFrame();

    // Open menu again and hover on td.b
    await hover(el.querySelector("td.b"));
    await animationFrame();
    await waitFor("[data-type='column'].o-we-table-menu");

    await click("[data-type='column'].o-we-table-menu");
    await animationFrame();
    expect("div[name='move_right']").toHaveClass("disabled");
    expect("div[name='move_left']").toHaveClass("disabled");

    // Close menu
    await click("[data-type='column'].o-we-table-menu");
    await animationFrame();

    // Open menu again and hover on td.c
    await hover(el.querySelector("td.c"));
    await animationFrame();
    await waitFor("[data-type='column'].o-we-table-menu");

    await click("[data-type='column'].o-we-table-menu");
    await animationFrame();
    expect("div[name='move_right']").not.toHaveClass("disabled");
    expect("div[name='move_left']").toHaveClass("disabled");
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
    await expectElementCount(".o-we-table-menu", 0);

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
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
            <tr><td class="c">3</td><td class="d">4</td></tr>
            <tr><td class="a">1[]</td><td class="b">2</td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
    );

    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td class="b">2</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
    );
});

test("move second row to top when first row is header row", async () => {
    const { el } = await setupEditor(
        unformat(`
        <table>
            <tbody>
                <tr><th class="o_table_header">1[]</th><th class="o_table_header">2</th></tr>
                <tr><td class="a">3</td><td>4</td></tr>
            </tbody>
        </table>`)
    );
    await expectElementCount(".o-we-table-menu", 0);

    // hover on td to show row ui
    await hover(el.querySelector("td.a"));
    await waitFor("[data-type='row'].o-we-table-menu");

    // click on it to open dropdown
    await click("[data-type='row'].o-we-table-menu");
    await waitFor("div[name='move_up']");

    // move row up
    await click("div[name='move_up']");
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr><th class="a o_table_header">3</th><th class="o_table_header">4</th></tr>
                <tr><td>1[]</td><td>2</td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
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
    await expectElementCount(".o-we-table-menu", 0);

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
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr><td style="width: 100px;" class="c">3</td><td style="width: 200px;" class="d">4</td></tr>
                <tr><td style="width: 100px;" class="a">1[]</td><td style="width: 200px;" class="b">2</td></tr>
                <tr><td style="width: 150px;" class="e">5</td><td style="width: 150px;" class="f">6</td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
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
    await expectElementCount(".o-we-table-menu", 0);

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
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
            <tr><td class="c">3</td><td class="d">4</td></tr>
            <tr><td class="a">1[]</td><td class="b">2</td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
    );

    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td class="b">2</td></tr>
                <tr><td class="c">3</td><td class="d">4</td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
    );
});

test("disables row move up or down when affected by rowspan in current or adjacent rows", async () => {
    const { el } = await setupEditor(
        unformat(`
        <table>
            <tbody>
                <tr><td><br></td><td><br></td></tr>
                <tr><td class="a"><br></td><td><br></td></tr>
                <tr><td class="b"><br></td><td rowspan="2"><br></td></tr>
                <tr><td><br></td></tr>
                <tr><td class="c"><br></td><td><br></td></tr>
                <tr><td><br></td><td><br></td></tr>
            </tbody>
        </table>`)
    );
    // Initially no menu visible
    await expectElementCount(".o-we-table-menu", 0);

    // Check on row "a"
    await hover(el.querySelector("td.a"));
    await waitFor("[data-type='row'].o-we-table-menu");
    await click("[data-type='row'].o-we-table-menu");
    await animationFrame();
    expect("div[name='move_down']").toHaveClass("disabled");
    expect("div[name='move_up']").not.toHaveClass("disabled");

    // Close menu
    await click("[data-type='row'].o-we-table-menu");
    await animationFrame();

    // Check on row "b" (covered by rowspan)
    await hover(el.querySelector("td.b"));
    await animationFrame();
    await waitFor("[data-type='row'].o-we-table-menu");
    await click("[data-type='row'].o-we-table-menu");
    await animationFrame();
    expect("div[name='move_down']").toHaveClass("disabled");
    expect("div[name='move_up']").toHaveClass("disabled");

    // Close menu
    await click("[data-type='row'].o-we-table-menu");
    await animationFrame();

    // Check on row "c"
    await hover(el.querySelector("td.c"));
    await animationFrame();
    await waitFor("[data-type='row'].o-we-table-menu");
    await click("[data-type='row'].o-we-table-menu");
    await animationFrame();
    expect("div[name='move_down']").not.toHaveClass("disabled");
    expect("div[name='move_up']").toHaveClass("disabled");
});

test("move header row below operation", async () => {
    const { el } = await setupEditor(
        unformat(`
        <table>
            <tbody>
                <tr><th class="a o_table_header">1[]</th><th class="o_table_header">2</th></tr>
                <tr><td>3</td><td>4</td></tr>
            </tbody>
        </table>`)
    );
    await expectElementCount(".o-we-table-menu", 0);

    // hover on th to show row ui
    await hover(el.querySelector("th.a"));
    await waitFor("[data-type='row'].o-we-table-menu");

    // click on it to open dropdown
    await click("[data-type='row'].o-we-table-menu");
    await waitFor("div[name='move_down']");

    // move row below
    await click("div[name='move_down']");
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr><th class="o_table_header">3</th><th class="o_table_header">4</th></tr>
                <tr><td class="a">1[]</td><td>2</td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
    );
});

test("should revert a converted header row back to normal after undo", async () => {
    const { el, editor } = await setupEditor(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">1[]</td><td>2</td></tr>
                <tr><td>3</td><td>4</td></tr>
            </tbody>
        </table>`)
    );
    await expectElementCount(".o-we-table-menu", 0);

    // hover on th to show row ui
    await hover(el.querySelector("td.a"));
    await waitFor("[data-type='row'].o-we-table-menu");

    // click on it to open dropdown
    await click("[data-type='row'].o-we-table-menu");
    await waitFor("div[name='make_header']");

    // convert row into header
    await click("div[name='make_header']");
    await animationFrame();
    expect(getContent(el)).toBe(
        unformat(`
            <p data-selection-placeholder=""><br></p>
            <table>
                <tbody>
                    <tr><th class="a o_table_header">1[]</th><th class="o_table_header">2</th></tr>
                    <tr><td>3</td><td>4</td></tr>
                </tbody>
            </table>
            <p data-selection-placeholder=""><br></p>
        `)
    );

    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
            <p data-selection-placeholder=""><br></p>
            <table>
                <tbody>
                    <tr><td class="a">1[]</td><td>2</td></tr>
                    <tr><td>3</td><td>4</td></tr>
                </tbody>
            </table>
            <p data-selection-placeholder=""><br></p>
        `)
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
    await expectElementCount(".o-we-table-menu", 0);

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
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr><td style="width: 100px;" class="c">3</td><td style="width: 200px;" class="d">4</td></tr>
                <tr><td style="width: 100px;" class="a">1[]</td><td style="width: 200px;" class="b">2</td></tr>
                <tr><td style="width: 150px;" class="e">5</td><td style="width: 150px;" class="f">6</td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
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
    await expectElementCount(".o-we-table-menu", 0);

    await hover(el.querySelector("td.a"));
    await waitFor(".o-we-table-menu");
    expect("[data-type='row'].o-we-table-menu").toHaveCount(1);

    await click("[data-type='row'].o-we-table-menu");
    await waitFor(".dropdown-menu");
    await click(queryOne(".dropdown-menu [name='reset_table_size']"));
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr><td style="" class="a">1[]</td></tr>
                <tr><td style="" class="b">2</td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
    );

    undo(editor);
    expect(getContent(el)).toBe(
        unformat(
            `<p data-selection-placeholder=""><br></p>
            <table style="width: 150px;">
            <tbody>
            <tr><td style="width: 100px;" class="a">1[]</td></tr>
            <tr><td style="width: 50px;" class="b">2</td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`
        )
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
    await expectElementCount(".o-we-table-menu", 0);

    await hover(el.querySelector("td.a"));
    await waitFor(".o-we-table-menu");
    expect("[data-type='row'].o-we-table-menu").toHaveCount(1);

    await click("[data-type='row'].o-we-table-menu");
    await waitFor(".dropdown-menu");
    await click(queryOne(".dropdown-menu [name='reset_table_size']"));
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr style=""><td class="a">1[]</td></tr>
                <tr style=""><td class="b">2</td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
    );

    undo(editor);
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
            <tr style="height: 100px;"><td class="a">1[]</td></tr>
            <tr style="height: 50px;"><td class="b">2</td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
    );
});

test("reset row size to remove custom height", async () => {
    const { el } = await setupEditor(
        unformat(`
        <table class="table table-bordered o_table">
            <tbody>
                <tr style="height: 38px;">
                    <td class="a">1</td>
                    <td class="b">2</td>
                    <td class="c">3</td>
                </tr>
                <tr style="height: 100px;">
                    <td class="d">4[]</td>
                    <td class="e">5</td>
                    <td class="f">6</td>
                </tr>
                <tr style="height: 38px;">
                    <td class="g">7</td>
                    <td class="h">8</td>
                    <td class="i">9</td>
                </tr>
            </tbody>
        </table>`)
    );
    await expectElementCount(".o-we-table-menu", 0);

    await hover(el.querySelector("td.d"));
    await waitFor(".o-we-table-menu");
    expect("[data-type='row'].o-we-table-menu").toHaveCount(1);

    await click("[data-type='row'].o-we-table-menu");
    await waitFor(".dropdown-menu", { timeout: 1000 });
    await click(queryOne(".dropdown-menu [name='reset_row_size']"));
    expect(getContent(el)).toBe(
        unformat(
            `<p data-selection-placeholder=""><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr style="">
                        <td class="a">1</td>
                        <td class="b">2</td>
                        <td class="c">3</td>
                    </tr>
                    <tr style="">
                        <td class="d">4[]</td>
                        <td class="e">5</td>
                        <td class="f">6</td>
                    </tr>
                    <tr style="">
                        <td class="g">7</td>
                        <td class="h">8</td>
                        <td class="i">9</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        )
    );
});

test("should redistribute excess width from current column to smaller columns", async () => {
    const { el } = await setupEditor(
        unformat(`
            <table class="table table-bordered o_table" style="width: 500px">
                <tbody>
                    <tr>
                        <td style="width: 100px;" class="a">1</td>
                        <td style="width: 120px;" class="b">2</td>
                        <td style="width: 60px;" class="c">3[]</td>
                        <td style="width: 120px;" class="d">4</td>
                        <td style="width: 100px;" class="e">5</td>
                    </tr>
                    <tr>
                        <td style="width: 100px;" class="f">6</td>
                        <td style="width: 120px;" class="g">7</td>
                        <td style="width: 60px;" class="h">8</td>
                        <td style="width: 120px;" class="i">9</td>
                        <td style="width: 100px;" class="j">10</td>
                    </tr>
                </tbody>
            </table>`)
    );
    await expectElementCount(".o-we-table-menu", 0);

    await hover(el.querySelector("td.c"));
    await waitFor(".o-we-table-menu");
    expect("[data-type='column'].o-we-table-menu").toHaveCount(1);

    await click("[data-type='column'].o-we-table-menu");
    await waitFor(".dropdown-menu", { timeout: 1000 });
    await click(queryOne(".dropdown-menu [name='reset_column_size']"));
    expect(getContent(el)).toBe(
        unformat(
            `<p data-selection-placeholder=""><br></p>
            <table class="table table-bordered o_table" style="width: 500px">
                <tbody>
                    <tr>
                        <td style="" class="a">1</td>
                        <td style="" class="b">2</td>
                        <td style="" class="c">3[]</td>
                        <td style="" class="d">4</td>
                        <td style="" class="e">5</td>
                    </tr>
                    <tr>
                        <td style="" class="f">6</td>
                        <td style="" class="g">7</td>
                        <td style="" class="h">8</td>
                        <td style="" class="i">9</td>
                        <td style="" class="j">10</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        )
    );
});

test("should redistribute excess width from larger columns to current column", async () => {
    const { el } = await setupEditor(
        unformat(`
            <table class="table table-bordered o_table" style="width: 700px">
                <tbody>
                    <tr>
                        <td style="width: 120px;" class="a">1</td>
                        <td style="width: 80px;" class="b">2</td>
                        <td style="width: 60px;" class="c">3</td>
                        <td style="width: 180px;" class="d">4[]</td>
                        <td style="width: 60px;" class="e">5</td>
                        <td style="width: 80px;" class="f">6</td>
                        <td style="width: 120px;" class="g">7</td>
                    </tr>
                    <tr>
                        <td style="width: 120px;" class="h">8</td>
                        <td style="width: 80px;" class="i">9</td>
                        <td style="width: 60px;" class="j">10</td>
                        <td style="width: 180px;" class="k">11</td>
                        <td style="width: 60px;" class="l">12</td>
                        <td style="width: 80px;" class="m">13</td>
                        <td style="width: 120px;" class="n">14</td>
                    </tr>
                </tbody>
            </table>`)
    );
    await expectElementCount(".o-we-table-menu", 0);

    await hover(el.querySelector("td.d"));
    await waitFor(".o-we-table-menu");
    expect("[data-type='column'].o-we-table-menu").toHaveCount(1);

    await click("[data-type='column'].o-we-table-menu");
    await waitFor(".dropdown-menu", { timeout: 1000 });
    await click(queryOne(".dropdown-menu [name='reset_column_size']"));
    expect(getContent(el)).toBe(
        unformat(
            `<p data-selection-placeholder=""><br></p>
            <table class="table table-bordered o_table" style="width: 700px">
                <tbody>
                    <tr>
                        <td style="width: 120px;" class="a">1</td>
                        <td style="width: 80px;" class="b">2</td>
                        <td style="" class="c">3</td>
                        <td style="" class="d">4[]</td>
                        <td style="" class="e">5</td>
                        <td style="width: 80px;" class="f">6</td>
                        <td style="width: 120px;" class="g">7</td>
                    </tr>
                    <tr>
                        <td style="width: 120px;" class="h">8</td>
                        <td style="width: 80px;" class="i">9</td>
                        <td style="" class="j">10</td>
                        <td style="" class="k">11</td>
                        <td style="" class="l">12</td>
                        <td style="width: 80px;" class="m">13</td>
                        <td style="width: 120px;" class="n">14</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        )
    );
});

test("applies alternating row colors when 'Insert Alternate Colors' option is clicked", async () => {
    const { el } = await setupEditor(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">1[]</td></tr>
                <tr><td>2</td></tr>
                <tr><td>3</td></tr>
                <tr><td>4</td></tr>
            </tbody>
        </table>`)
    );
    await expectElementCount(".o-we-table-menu", 0);
    const cells = queryAll("tr > :first-child");
    const firstRowCellColor = getComputedStyle(cells[0]).backgroundColor;
    expect(
        cells.every((cell) => getComputedStyle(cell).backgroundColor === firstRowCellColor)
    ).toBe(true);

    await hover(el.querySelector("td.a"));
    await waitFor(".o-we-table-menu");

    expect("[data-type='row'].o-we-table-menu").toHaveCount(1);
    await click("[data-type='row'].o-we-table-menu");
    await waitFor(".dropdown-menu");
    await expectElementCount("div[name='toggle_alternating_rows'", 1);
    expect("div[name='toggle_alternating_rows'").toHaveText("Alternate row colors");
    await click("div[name='toggle_alternating_rows'");
    expect(getContent(el)).toBe(
        unformat(`
            <p data-selection-placeholder=""><br></p>
            <table class="o_alternating_rows">
                <tbody>
                    <tr><td class="a">1[]</td></tr>
                    <tr><td>2</td></tr>
                    <tr><td>3</td></tr>
                    <tr><td>4</td></tr>
                </tbody>
            </table>
            <p data-selection-placeholder=""><br></p>`)
    );
    expect(getComputedStyle(cells[2]).backgroundColor).toBe(firstRowCellColor);
    const secondRowCellColor = getComputedStyle(cells[1]).backgroundColor;
    expect(secondRowCellColor).not.toBe(firstRowCellColor);
    expect(getComputedStyle(cells[3]).backgroundColor).toBe(secondRowCellColor);
});

test("removes alternating row colors when 'Clear Alternate Colors' option is clicked", async () => {
    const { el } = await setupEditor(
        unformat(`
        <table class="o_alternating_rows">
            <tbody>
                <tr><td class="a">1[]</td></tr>
                <tr><td>2</td></tr>
                <tr><td>3</td></tr>
                <tr><td>4</td></tr>
            </tbody>
        </table>`)
    );
    await expectElementCount(".o-we-table-menu", 0);

    const cells = queryAll("tr > :first-child");
    const firstRowCellColor = getComputedStyle(cells[0]).backgroundColor;
    const secondRowCellColor = getComputedStyle(cells[1]).backgroundColor;
    expect(getComputedStyle(cells[2]).backgroundColor).toBe(firstRowCellColor);
    expect(secondRowCellColor).not.toBe(firstRowCellColor);
    expect(getComputedStyle(cells[3]).backgroundColor).toBe(secondRowCellColor);

    await hover(el.querySelector("td.a"));
    await waitFor(".o-we-table-menu");

    expect("[data-type='row'].o-we-table-menu").toHaveCount(1);
    await click("[data-type='row'].o-we-table-menu");
    await waitFor(".dropdown-menu");
    await expectElementCount("div[name='toggle_alternating_rows'", 1);
    expect("div[name='toggle_alternating_rows'").toHaveText("Clear alternate colors");
    await click("div[name='toggle_alternating_rows'");
    expect(getContent(el)).toBe(
        unformat(`
            <p data-selection-placeholder=""><br></p>
            <table class="">
                <tbody>
                    <tr><td class="a">1[]</td></tr>
                    <tr><td>2</td></tr>
                    <tr><td>3</td></tr>
                    <tr><td>4</td></tr>
                </tbody>
            </table>
            <p data-selection-placeholder=""><br></p>`)
    );
    expect(
        cells.every((cell) => getComputedStyle(cell).backgroundColor === firstRowCellColor)
    ).toBe(true);
});

describe("Disable table merge options", () => {
    test("disables both merge options when selection spans multiple rows and columns", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td class="a"><p>[<br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="b"><p><br></p></td>
                            <td><p><br>]</p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>`)
        );
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td class="a o_selected_td"><p>[<br></p></td>
                            <td class="o_selected_td"><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="b o_selected_td"><p><br></p></td>
                            <td class="o_selected_td"><p><br>]</p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
        await expectElementCount(".o-we-table-menu", 0);

        // hover on td to show col ui
        await hover(el.querySelector("td.a"));
        await waitFor("[data-type='column'].o-we-table-menu");

        // click on it to open dropdown
        await click("[data-type='column'].o-we-table-menu");
        await waitFor("div[name='merge_cell']");

        expect("div[name='merge_cell']").toHaveClass("disabled");

        // click on menu to close dropdown
        await click("[data-type='column'].o-we-table-menu");
        await animationFrame();

        // hover on td to show col ui
        await hover(el.querySelector("td.b"));
        await waitFor("[data-type='row'].o-we-table-menu");

        // click on it to open dropdown
        await click("[data-type='row'].o-we-table-menu");
        await waitFor("div[name='merge_cell']");

        expect("div[name='merge_cell']").toHaveClass("disabled");
    });

    test("disables merge row option when selection includes cells with rowspan", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td rowspan="2"><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a">[<p><br></p></td>
                            <td><p><br></p>]</td>
                        </tr>
                    </tbody>
                </table>`)
        );
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td rowspan="2" class="o_selected_td"><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a o_selected_td">[<p><br></p></td>
                            <td class="o_selected_td"><p><br></p>]</td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );

        await expectElementCount(".o-we-table-menu", 0);

        // hover on td to show col ui
        await hover(el.querySelector("td.a"));
        await waitFor("[data-type='row'].o-we-table-menu");

        // click on it to open dropdown
        await click("[data-type='row'].o-we-table-menu");
        await waitFor("div[name='merge_cell']");

        expect("div[name='merge_cell']").toHaveClass("disabled");
    });
    test("disables merge column option when selection includes cells with colspan", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td class="a"><p>[<br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td colspan="3"><p>]<br></p></td>
                        </tr>
                    </tbody>
                </table>`)
        );
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td class="a o_selected_td"><p>[<br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td colspan="3" class="o_selected_td"><p>]<br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );

        await expectElementCount(".o-we-table-menu", 0);

        // hover on td to show col ui
        await hover(el.querySelector("td.a"));
        await waitFor("[data-type='column'].o-we-table-menu");

        // click on it to open dropdown
        await click("[data-type='column'].o-we-table-menu");
        await waitFor("div[name='merge_cell']");

        expect("div[name='merge_cell']").toHaveClass("disabled");
    });
});

describe("Merge column cells", () => {
    test("merges selected cells in a single row into one with colspan", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a">[<p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p>]</td>
                        </tr>
                    </tbody>
                </table>`)
        );
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a o_selected_td">[<p><br></p></td>
                            <td class="o_selected_td"><p><br></p></td>
                            <td class="o_selected_td"><p><br></p>]</td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );

        await expectElementCount(".o-we-table-menu", 0);

        // hover on td to show col ui
        await hover(el.querySelector("td.a"));
        await waitFor("[data-type='row'].o-we-table-menu");

        // click on it to open dropdown
        await click("[data-type='row'].o-we-table-menu");
        await waitFor("div[name='merge_cell']");

        await click("div[name='merge_cell']");
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a o_selected_td" colspan="3"><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
    });

    test("merges selected filled cells by combining their content into one cell with colspan", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a">[<p>a</p></td>
                            <td><p>b</p></td>
                            <td><p>c</p>]</td>
                        </tr>
                    </tbody>
                </table>`)
        );
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a o_selected_td">[<p>a</p></td>
                            <td class="o_selected_td"><p>b</p></td>
                            <td class="o_selected_td"><p>c</p>]</td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
        await expectElementCount(".o-we-table-menu", 0);

        // hover on td to show col ui
        await hover(el.querySelector("td.a"));
        await waitFor("[data-type='row'].o-we-table-menu");

        // click on it to open dropdown
        await click("[data-type='row'].o-we-table-menu");
        await waitFor("div[name='merge_cell'");

        await click("div[name='merge_cell']");
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a o_selected_td" colspan="3"><p>[a</p><p>b</p><p>c]</p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
    });
});

describe("Merge row cells", () => {
    test("merges selected cells vertically in a column by applying rowspan", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td class="a"><p>[<br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td><p><br>]</p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>`)
        );
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td class="a o_selected_td"><p>[<br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="o_selected_td"><p><br>]</p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );

        await expectElementCount(".o-we-table-menu", 0);

        // hover on td to show col ui
        await hover(el.querySelector("td.a"));
        await waitFor("[data-type='column'].o-we-table-menu");

        // click on it to open dropdown
        await click("[data-type='column'].o-we-table-menu");
        await waitFor("div[name='merge_cell']");

        await click("div[name='merge_cell']");
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td class="a o_selected_td" rowspan="2"><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
    });

    test("merges filled cells vertically by combining their content into one cell with rowspan", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td class="a"><p>[a</p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td><p>b]</p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>`)
        );
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td class="a o_selected_td"><p>[a</p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="o_selected_td"><p>b]</p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
        await expectElementCount(".o-we-table-menu", 0);

        // hover on td to show col ui
        await hover(el.querySelector("td.a"));
        await waitFor("[data-type='column'].o-we-table-menu");

        // click on it to open dropdown
        await click("[data-type='column'].o-we-table-menu");
        await waitFor("div[name='merge_cell'");

        await click("div[name='merge_cell']");
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td class="a o_selected_td" rowspan="2"><p>[a</p><p>b]</p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
    });

    test("does not display merge cell option when hovering over a table that has no selected cells", async () => {
        const { el } = await setupEditor(
            unformat(`
                <p><br></p>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td class="a"><p>[<br></p></td>
                            <td><p><br>]</p></td>
                        </tr>
                    </tbody>
                </table>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td class="b"><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>`)
        );
        expect(getContent(el)).toBe(
            unformat(`
                <p><br></p>
                <table class="table table-bordered o_table o_selected_table">
                    <tbody>
                        <tr>
                            <td class="a o_selected_td"><p>[<br></p></td>
                            <td class="o_selected_td"><p><br>]</p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td class="b"><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
        await expectElementCount(".o-we-table-menu", 0);
        await hover(el.querySelector("td.b"));
        await waitFor("[data-type='column'].o-we-table-menu");
        await click("[data-type='column'].o-we-table-menu");
        await animationFrame();
        expect("div[name='merge_cell']").toHaveCount(0);
        await click("[data-type='column'].o-we-table-menu");
        await animationFrame();
    });
});

describe("unmerge cells option", () => {
    test("unmerge merged row cells via column menu", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td class="a" rowspan="2"><p>[]<br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>`)
        );
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td class="a" rowspan="2"><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
        await expectElementCount(".o-we-table-menu", 0);

        // hover on td to show col ui
        await hover(el.querySelector("td.a"));
        await waitFor("[data-type='column'].o-we-table-menu");

        // click on it to open dropdown
        await click("[data-type='column'].o-we-table-menu");
        await animationFrame();
        expect("div[name='unmerge_cell']").toHaveCount(1);

        await click("div[name='unmerge_cell']");
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td class="a"><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
    });
    test("unmerge merged column cells via row menu", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a" colspan="3"><p>[]<br></p></td>
                        </tr>
                    </tbody>
                </table>`)
        );
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a" colspan="3"><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
        await expectElementCount(".o-we-table-menu", 0);

        // hover on td to show col ui
        await hover(el.querySelector("td.a"));
        await waitFor("[data-type='row'].o-we-table-menu");

        // click on it to open dropdown
        await waitFor("[data-type='row'].o-we-table-menu");
        await click("[data-type='row'].o-we-table-menu");
        await animationFrame();
        expect("div[name='unmerge_cell']").toHaveCount(1);

        await click("div[name='unmerge_cell']");
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a"><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
    });
    test("unmerge merged filled row cells via column menu", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td class="a" rowspan="2"><p>a[]</p><p>b</p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>`)
        );
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td class="a" rowspan="2"><p>a[]</p><p>b</p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
        await expectElementCount(".o-we-table-menu", 0);

        // hover on td to show col ui
        await hover(el.querySelector("td.a"));
        await waitFor("[data-type='column'].o-we-table-menu");

        // click on it to open dropdown
        await click("[data-type='column'].o-we-table-menu");
        await animationFrame();
        expect("div[name='unmerge_cell']").toHaveCount(1);

        await click("div[name='unmerge_cell']");
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td class="a"><p>a[]</p><p>b</p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
    });
    test("unmerge merged filled column cells via row menu", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a" colspan="3"><p>a[]</p><p>b</p></td>
                        </tr>
                    </tbody>
                </table>`)
        );
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a" colspan="3"><p>a[]</p><p>b</p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
        await expectElementCount(".o-we-table-menu", 0);

        // hover on td to show col ui
        await hover(el.querySelector("td.a"));
        await waitFor("[data-type='row'].o-we-table-menu");

        // click on it to open dropdown
        await waitFor("[data-type='row'].o-we-table-menu");
        await click("[data-type='row'].o-we-table-menu");
        await animationFrame();
        expect("div[name='unmerge_cell']").toHaveCount(1);

        await click("div[name='unmerge_cell']");
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td class="a"><p>a[]</p><p>b</p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`)
        );
    });
});
