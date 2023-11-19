import { expect, test } from "@odoo/hoot";
import {
    click,
    hover,
    queryOne,
    waitFor,
    waitForNone,
    manuallyDispatchProgrammaticEvent,
} from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { setupEditor } from "../_helpers/editor";
import { getContent } from "../_helpers/selection";
import { unformat } from "../_helpers/format";

function availableCommands(menu) {
    return [...menu.querySelectorAll("span div.user-select-none")].map((n) =>
        n.getAttribute("name")
    );
}

/**
 * Dispatch a mousemove event on the given element.
 *
 * @param {HTMLElement} el
 * @param {number} x
 * @param {number} y
 */
function dispatchMousemove(el, x, y) {
    const eventInit = {
        clientX: x,
        clientY: y,
        pageX: x,
        pageY: y,
        relatedTarget: null,
        screenX: x,
        screenY: y,
    };

    const moveEvent = manuallyDispatchProgrammaticEvent(el, "pointermove", eventInit);
    if (!moveEvent.defaultPrevented) {
        manuallyDispatchProgrammaticEvent(el, "mousemove", eventInit);
    }
}

test("should only display the table ui menu if the table isContentEditable=true", async () => {
    const { el } = await setupEditor(`
        <table><tbody><tr>
            <td>11[]</td>
        </tr></tbody></table>`);
    expect(".o-we-table-menu").toHaveCount(0);

    hover(el.querySelector("td"));
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

    hover(el.querySelector("td.a"));
    await waitFor(".o-we-table-menu");
    expect("[data-type='column'].o-we-table-menu").toHaveCount(1);
    expect("[data-type='row'].o-we-table-menu").toHaveCount(1);

    hover(el.querySelector("td.b"));
    await waitForNone("[data-type='row'].o-we-table-menu");
    expect("[data-type='column'].o-we-table-menu").toHaveCount(1);

    hover(el.querySelector("td.c"));
    await waitForNone("[data-type='column'].o-we-table-menu");
    expect("[data-type='row'].o-we-table-menu").toHaveCount(1);

    hover(el.querySelector("td.d"));
    await waitForNone(".o-we-table-menu");
});

test("should not display the table ui menu if the table element isContentEditable=false", async () => {
    const { el } = await setupEditor(`
        <table contenteditable="false"><tbody><tr>
            <td>11[]</td>
        </tr></tbody></table>`);
    expect(".o-we-table-menu").toHaveCount(0);

    hover(el.querySelector("td"));
    await animationFrame();
    expect(".o-we-table-menu").toHaveCount(0);
});

test("should not display the table ui menu if we leave the editor content", async () => {
    const { el } = await setupEditor(`
        <table><tbody><tr>
            <td>11[]</td>
        </tr></tbody></table>`);
    expect(".o-we-table-menu").toHaveCount(0);

    hover(el.querySelector("td"));
    await animationFrame();
    expect(".o-we-table-menu").toHaveCount(2);

    hover(el.parentElement);
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

        dispatchMousemove(td, x, y);

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

    hover(el.querySelector("td"));

    await animationFrame();
    expect(".o_col_resize").toHaveCount(0);
});

test("list of table commands in first column", async () => {
    const { el } = await setupEditor(`
        <table>
            <tbody>
            <tr><td class="a">1[]</td><td class="b">2</td><td class="c">3</td></tr>
            </tbody>
        </table>`);
    expect(".o-we-table-menu").toHaveCount(0);

    // check list of commands on first column
    hover(el.querySelector("td.a"));
    await waitFor(".o-we-table-menu");
    expect("[data-type='column'].o-we-table-menu").toHaveCount(1);
    expect("[data-type='row'].o-we-table-menu").toHaveCount(1);
    click("[data-type='column'].o-we-table-menu");
    await waitFor(".dropdown-menu");
    hover(el);
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
    hover(el.querySelector("td.b"));
    await waitFor(".o-we-table-menu");
    expect("[data-type='column'].o-we-table-menu").toHaveCount(1);
    click("[data-type='column'].o-we-table-menu");
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
    hover(el.querySelector("td.c"));
    await waitFor(".o-we-table-menu");
    expect("[data-type='column'].o-we-table-menu").toHaveCount(1);
    click("[data-type='column'].o-we-table-menu");
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
    hover(el.querySelector("td.a"));
    await waitFor(".o-we-table-menu");
    expect("[data-type='column'].o-we-table-menu").toHaveCount(1);
    expect("[data-type='row'].o-we-table-menu").toHaveCount(1);
    click("[data-type='row'].o-we-table-menu");
    await waitFor(".dropdown-menu");
    hover(el);
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
    hover(el.querySelector("td.b"));
    await waitFor(".o-we-table-menu");
    expect("[data-type='row'].o-we-table-menu").toHaveCount(1);
    click("[data-type='row'].o-we-table-menu");
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
    hover(el.querySelector("td.c"));
    await waitFor(".o-we-table-menu");
    expect("[data-type='row'].o-we-table-menu").toHaveCount(1);
    click("[data-type='row'].o-we-table-menu");
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
    hover(el.querySelector("td.a"));
    await waitFor(".o-we-table-menu");
    expect("[data-type='column'].o-we-table-menu").toHaveCount(1);
    expect("[data-type='row'].o-we-table-menu").toHaveCount(1);

    click("[data-type='row'].o-we-table-menu");
    await waitFor(".dropdown-menu");
    click("[data-type='row'].o-we-table-menu");
    await animationFrame();
    expect("[data-type='column'].o-we-table-menu").toHaveCount(0);
    expect("[data-type='row'].o-we-table-menu").toHaveCount(1);
    expect(".dropdown-menu").toHaveCount(0);

    hover(el);
    await animationFrame();
    expect("[data-type='column'].o-we-table-menu").toHaveCount(0);
    expect("[data-type='row'].o-we-table-menu").toHaveCount(0);
    expect(".dropdown-menu").toHaveCount(0);
});

test("basic delete column operation", async () => {
    const { el } = await setupEditor(
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
    hover(el.querySelector("td.b"));
    await waitFor(".o-we-table-menu");

    // click on it to open dropdown
    click(".o-we-table-menu");
    await waitFor("div[name='delete']");

    // delete column
    click("div[name='delete']");
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
});

test("basic delete row operation", async () => {
    const { el } = await setupEditor(
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
    hover(el.querySelector("td.c"));
    await waitFor(".o-we-table-menu");

    // click on it to open dropdown
    click(".o-we-table-menu");
    await waitFor("div[name='delete']");

    // delete row
    click("div[name='delete']");
    // not sure about selection...
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
                <tr><td class="a">[]1</td><td class="b">2</td></tr>
            </tbody>
        </table>`)
    );
});

test("insert column left operation", async () => {
    const { el } = await setupEditor(
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
    hover(el.querySelector("td.b"));
    await waitFor(".o-we-table-menu");

    // click on it to open dropdown
    click(".o-we-table-menu");
    await waitFor("div[name='insert_left']");

    // insert column left
    click("div[name='insert_left']");
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
});

test("insert column right operation", async () => {
    const { el } = await setupEditor(
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
    hover(el.querySelector("td.a"));
    await waitFor("[data-type='column'].o-we-table-menu");

    // click on it to open dropdown
    click("[data-type='column'].o-we-table-menu");
    await waitFor("div[name='insert_right']");

    // insert column right
    click("div[name='insert_right']");
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
});

test("insert row above operation", async () => {
    const { el } = await setupEditor(
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
    hover(el.querySelector("td.c"));
    await waitFor(".o-we-table-menu");

    // click on it to open dropdown
    click(".o-we-table-menu");
    await waitFor("div[name='insert_above']");

    // insert row above
    click("div[name='insert_above']");
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
});

test("insert row below operation", async () => {
    const { el } = await setupEditor(
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
    hover(el.querySelector("td.a"));
    await waitFor("[data-type='row'].o-we-table-menu");

    // click on it to open dropdown
    click("[data-type='row'].o-we-table-menu");
    await waitFor("div[name='insert_below']");

    // insert row below
    click("div[name='insert_below']");
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
});

test("move column left operation", async () => {
    const { el } = await setupEditor(
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
    hover(el.querySelector("td.b"));
    await waitFor("[data-type='column'].o-we-table-menu");

    // click on it to open dropdown
    click("[data-type='column'].o-we-table-menu");
    await waitFor("div[name='move_left']");

    // move column left
    click("div[name='move_left']");
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
            <tr><td class="b">2[]</td><td class="a">1</td></tr>
            <tr><td class="d">4</td><td class="c">3</td></tr>
            </tbody>
        </table>`)
    );
});

test("move column right operation", async () => {
    const { el } = await setupEditor(
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
    hover(el.querySelector("td.a"));
    await waitFor("[data-type='column'].o-we-table-menu");

    // click on it to open dropdown
    click("[data-type='column'].o-we-table-menu");
    await waitFor("div[name='move_right']");

    // move column right
    click("div[name='move_right']");
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
            <tr><td class="b">2[]</td><td class="a">1</td></tr>
            <tr><td class="d">4</td><td class="c">3</td></tr>
            </tbody>
        </table>`)
    );
});

test("move row above operation", async () => {
    const { el } = await setupEditor(
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
    hover(el.querySelector("td.c"));
    await waitFor("[data-type='row'].o-we-table-menu");

    // click on it to open dropdown
    click("[data-type='row'].o-we-table-menu");
    await waitFor("div[name='move_up']");

    // move row up
    click("div[name='move_up']");
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
            <tr><td class="c">3</td><td class="d">4</td></tr>
            <tr><td class="a">1[]</td><td class="b">2</td></tr>
            </tbody>
        </table>`)
    );
});

test("move row below operation", async () => {
    const { el } = await setupEditor(
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
    hover(el.querySelector("td.a"));
    await waitFor("[data-type='row'].o-we-table-menu");

    // click on it to open dropdown
    click("[data-type='row'].o-we-table-menu");
    await waitFor("div[name='move_down']");

    // move row below
    click("div[name='move_down']");
    expect(getContent(el)).toBe(
        unformat(`
        <table>
            <tbody>
            <tr><td class="c">3</td><td class="d">4</td></tr>
            <tr><td class="a">1[]</td><td class="b">2</td></tr>
            </tbody>
        </table>`)
    );
});
