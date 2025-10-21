import { expect, test } from "@odoo/hoot";
import { click, hover, queryAllAttributes, queryOne, waitFor, waitForNone } from "@odoo/hoot-dom";
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
                <tr><th class="o_table_header">3</th><th class="o_table_header">4</th></tr>
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
                <tr><td>1[]</td><td>2</td></tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>`)
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
