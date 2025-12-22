import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { setupEditor } from "../_helpers/editor";
import { getContent } from "../_helpers/selection";
import { insertText } from "../_helpers/user_actions";
import { unformat } from "../_helpers/format";
import { press, waitFor, queryOne } from "@odoo/hoot-dom";
import { expectElementCount } from "../_helpers/ui_expectations";

function expectContentToBe(el, html) {
    expect(getContent(el)).toBe(unformat(html));
}

test.tags("desktop");
test("can add a table using the powerbox and keyboard", async () => {
    const { el, editor } = await setupEditor("<p>a[]</p>");
    await expectElementCount(".o-we-powerbox", 0);
    expectContentToBe(el, `<p>a[]</p>`);

    // open powerbox
    await insertText(editor, "/");
    await waitFor(".o-we-powerbox");
    await expectElementCount(".o-we-tablepicker", 0);

    // filter to get table command in first position
    await insertText(editor, "table");
    await animationFrame();

    // press enter to open tablepicker
    await press("Enter");
    await waitFor(".o-we-tablepicker");
    await expectElementCount(".o-we-powerbox", 0);

    // press enter to validate current dimension (3x3)
    await press("Enter");
    await animationFrame();
    await expectElementCount(".o-we-powerbox", 0);
    await expectElementCount(".o-we-tablepicker", 0);
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

test.tags("desktop");
test("can close table picker with escape", async () => {
    const { el, editor } = await setupEditor("<p>a[]</p>");
    await insertText(editor, "/");
    await waitFor(".o-we-powerbox");
    await insertText(editor, "table");
    expectContentToBe(el, "<p>a/table[]</p>");
    await animationFrame();
    await press("Enter");
    await expectElementCount(".o-we-tablepicker", 1);
    expectContentToBe(el, "<p>a[]</p>");
    await press("escape");
    await animationFrame();
    await expectElementCount(".o-we-tablepicker", 0);
});

test.tags("iframe", "desktop");
test("in iframe, can add a table using the powerbox and keyboard", async () => {
    const { el, editor } = await setupEditor("<p>a[]</p>", {
        props: { iframe: true },
    });
    await expectElementCount(".o-we-powerbox", 0);
    expect(getContent(el)).toBe(`<p>a[]</p>`);
    expect(":iframe .o_table").toHaveCount(0);

    // open powerbox
    await insertText(editor, "/");
    await waitFor(".o-we-powerbox");
    await expectElementCount(".o-we-tablepicker", 0);

    // filter to get table command in first position
    await insertText(editor, "table");
    await animationFrame();

    // press enter to open tablepicker
    await press("Enter");
    await waitFor(".o-we-tablepicker");
    await expectElementCount(".o-we-powerbox", 0);

    // press enter to validate current dimension (3x3)
    await press("Enter");
    await animationFrame();
    await expectElementCount(".o-we-powerbox", 0);
    await expectElementCount(".o-we-tablepicker", 0);
    expect(":iframe .o_table").toHaveCount(1);
});

test.tags("desktop");
test("Expand columns in the correct direction in 'rtl'", async () => {
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

test.tags("desktop");
test("add table inside empty list", async () => {
    const { el, editor } = await setupEditor("<ul><li>[]<br></li></ul>");

    // open powerbox
    insertText(editor, "/");
    await waitFor(".o-we-powerbox");
    await expectElementCount(".o-we-tablepicker", 0);

    // filter to get table command in first position
    insertText(editor, "table");
    await animationFrame();

    // press enter to open tablepicker
    await press("Enter");
    await waitFor(".o-we-tablepicker");
    await expectElementCount(".o-we-powerbox", 0);

    // press enter to validate current dimension (3x3)
    await press("Enter");
    await animationFrame();
    await expectElementCount(".o-we-powerbox", 0);
    await expectElementCount(".o-we-tablepicker", 0);
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

test.tags("desktop");
test("add table inside non-empty list", async () => {
    const { el, editor } = await setupEditor("<ul><li>abc[]</li></ul>");

    // open powerbox
    insertText(editor, "/");
    await waitFor(".o-we-powerbox");
    await expectElementCount(".o-we-tablepicker", 0);

    // filter to get table command in first position
    insertText(editor, "table");
    await animationFrame();

    // press enter to open tablepicker
    await press("Enter");
    await waitFor(".o-we-tablepicker");
    await expectElementCount(".o-we-powerbox", 0);

    // press enter to validate current dimension (3x3)
    await press("Enter");
    await animationFrame();
    await expectElementCount(".o-we-powerbox", 0);
    await expectElementCount(".o-we-tablepicker", 0);
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
    await expectElementCount(".o-we-tablepicker", 1);
    expectContentToBe(el, "<p>a[]</p>");
    await insertText(editor, "b");
    await animationFrame();
    await expectElementCount(".o-we-tablepicker", 0);
    expectContentToBe(el, "<p>ab[]</p>");
    await insertText(editor, "/");
    await waitFor(".o-we-powerbox");
    await insertText(editor, "table");
    expectContentToBe(el, "<p>ab/table[]</p>");
    await animationFrame();
    await press("Enter");
    await expectElementCount(".o-we-tablepicker", 1);
    expectContentToBe(el, "<p>ab[]</p>");
    await insertText(editor, "/");
    await animationFrame();
    await expectElementCount(".o-we-tablepicker", 0);
});
