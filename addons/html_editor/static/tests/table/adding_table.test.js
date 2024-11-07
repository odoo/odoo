import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { setupEditor } from "../_helpers/editor";
import { getContent } from "../_helpers/selection";
import { insertText } from "../_helpers/user_actions";
import { unformat } from "../_helpers/format";
import { press, waitFor, queryOne } from "@odoo/hoot-dom";

function expectContentToBe(el, html) {
    expect(getContent(el)).toBe(unformat(html));
}

test.tags("desktop")("can add a table using the powerbox and keyboard", async () => {
    const { el, editor } = await setupEditor("<p>a[]</p>");
    expect(".o-we-powerbox").toHaveCount(0);
    expectContentToBe(el, `<p>a[]</p>`);

    // open powerbox
    await insertText(editor, "/");
    await waitFor(".o-we-powerbox");
    expect(".o-we-tablepicker").toHaveCount(0);

    // filter to get table command in first position
    await insertText(editor, "table");
    await animationFrame();

    // press enter to open tablepicker
    await press("Enter");
    await waitFor(".o-we-tablepicker");
    expect(".o-we-powerbox").toHaveCount(0);

    // press enter to validate current dimension (3x3)
    await press("Enter");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(0);
    expect(".o-we-tablepicker").toHaveCount(0);
    expectContentToBe(
        el,
        `<p>a</p>
        <table class="table table-bordered o_table">
            <tbody>
                <tr>
                    <td><p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p></td>
                    <td><p><br></p></td>
                    <td><p><br></p></td>
                </tr>
                <tr>
                    <td><p><br></p></td>
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
        <p><br></p>`
    );
});

test.tags("desktop")("can close table picker with escape", async () => {
    const { el, editor } = await setupEditor("<p>a[]</p>");
    await insertText(editor, "/");
    await waitFor(".o-we-powerbox");
    await insertText(editor, "table");
    expectContentToBe(el, "<p>a/table[]</p>");
    await animationFrame();
    await press("Enter");
    await waitFor(".o-we-tablepicker");
    expect(".o-we-tablepicker").toHaveCount(1);
    expectContentToBe(el, "<p>a[]</p>");
    await press("escape");
    await animationFrame();
    expect(".o-we-tablepicker").toHaveCount(0);
});

test.tags("iframe", "desktop");
test("in iframe, can add a table using the powerbox and keyboard", async () => {
    const { el, editor } = await setupEditor("<p>a[]</p>", {
        props: { iframe: true },
    });
    expect(".o-we-powerbox").toHaveCount(0);
    expect(getContent(el)).toBe(`<p>a[]</p>`);
    expect(":iframe .o_table").toHaveCount(0);

    // open powerbox
    await insertText(editor, "/");
    await waitFor(".o-we-powerbox");
    expect(".o-we-tablepicker").toHaveCount(0);

    // filter to get table command in first position
    await insertText(editor, "table");
    await animationFrame();

    // press enter to open tablepicker
    await press("Enter");
    await waitFor(".o-we-tablepicker");
    expect(".o-we-powerbox").toHaveCount(0);

    // press enter to validate current dimension (3x3)
    await press("Enter");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(0);
    expect(".o-we-tablepicker").toHaveCount(0);
    expect(":iframe .o_table").toHaveCount(1);
});

test.tags("desktop")("Expand columns in the correct direction in 'rtl'", async () => {
    const { editor } = await setupEditor("<p>a[]</p>", {
        config: {
            direction: "rtl",
        },
    });
    await insertText(editor, "/table");
    await press("Enter");
    await waitFor(".o-we-tablepicker");

    // Initially we have 3 columns
    const tablePickerOverlay = queryOne(".overlay");
    expect(tablePickerOverlay).toHaveStyle({ right: /px$/ });
    const right = tablePickerOverlay.style.right;
    const width3Columns = tablePickerOverlay.getBoundingClientRect().width;
    expect(".o-we-cell.active").toHaveCount(9);

    // Add one column -> we have 4 columns
    await press("ArrowLeft");
    await animationFrame();
    expect(tablePickerOverlay.getBoundingClientRect().width).toBeGreaterThan(width3Columns);
    expect(tablePickerOverlay).toHaveStyle({ right });
    expect(".o-we-cell.active").toHaveCount(12);

    // Remove one column -> we have 3 columns
    await press("ArrowRight");
    await animationFrame();
    expect(".o-we-cell.active").toHaveCount(9);
    expect(tablePickerOverlay).toHaveStyle({ right });

    // Remove one column -> we have 2 columns
    await press("ArrowRight");
    await animationFrame();
    expect(tablePickerOverlay.getBoundingClientRect().width).toBeLessThan(width3Columns);
    expect(tablePickerOverlay).toHaveStyle({ right });
    expect(".o-we-cell.active").toHaveCount(6);
});

test.tags("desktop")("add table inside empty list", async () => {
    const { el, editor } = await setupEditor("<ul><li>[]<br></li></ul>");

    // open powerbox
    insertText(editor, "/");
    await waitFor(".o-we-powerbox");
    expect(".o-we-tablepicker").toHaveCount(0);

    // filter to get table command in first position
    insertText(editor, "table");
    await animationFrame();

    // press enter to open tablepicker
    await press("Enter");
    await waitFor(".o-we-tablepicker");
    expect(".o-we-powerbox").toHaveCount(0);

    // press enter to validate current dimension (3x3)
    await press("Enter");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(0);
    expect(".o-we-tablepicker").toHaveCount(0);
    expectContentToBe(
        el,
        `<ul>
            <li>
                <br>
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td><p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
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
                <br>
            </li>
        </ul>`
    );
});

test.tags("desktop")("add table inside non-empty list", async () => {
    const { el, editor } = await setupEditor("<ul><li>abc[]</li></ul>");

    // open powerbox
    insertText(editor, "/");
    await waitFor(".o-we-powerbox");
    expect(".o-we-tablepicker").toHaveCount(0);

    // filter to get table command in first position
    insertText(editor, "table");
    await animationFrame();

    // press enter to open tablepicker
    await press("Enter");
    await waitFor(".o-we-tablepicker");
    expect(".o-we-powerbox").toHaveCount(0);

    // press enter to validate current dimension (3x3)
    await press("Enter");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(0);
    expect(".o-we-tablepicker").toHaveCount(0);
    expectContentToBe(
        el,
        `<ul>
            <li>
                abc
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td><p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
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
                <br>
            </li>
        </ul>`
    );
});

test.tags("desktop");
test("should close the table picker when any key except arrow keys pressed", async () => {
    const { el, editor } = await setupEditor("<p>a[]</p>");
    await insertText(editor, "/");
    await waitFor(".o-we-powerbox");
    await insertText(editor, "table");
    expectContentToBe(el, "<p>a/table[]</p>");
    await animationFrame();
    await press("Enter");
    await waitFor(".o-we-tablepicker");
    expect(".o-we-tablepicker").toHaveCount(1);
    expectContentToBe(el, "<p>a[]</p>");
    await insertText(editor, "b");
    await animationFrame();
    expect(".o-we-tablepicker").toHaveCount(0);
    expectContentToBe(el, "<p>ab[]</p>");
    await insertText(editor, "/");
    await waitFor(".o-we-powerbox");
    await insertText(editor, "table");
    expectContentToBe(el, "<p>ab/table[]</p>");
    await animationFrame();
    await press("Enter");
    await waitFor(".o-we-tablepicker");
    expect(".o-we-tablepicker").toHaveCount(1);
    expectContentToBe(el, "<p>ab[]</p>");
    await insertText(editor, "/");
    await animationFrame();
    expect(".o-we-tablepicker").toHaveCount(0);
});
