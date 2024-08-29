import { expect, test } from "@odoo/hoot";
import { setSelection } from "./_helpers/selection";
import { click, hover, queryAll, queryOne, waitFor, waitForNone } from "@odoo/hoot-dom";
import { defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";
import { animationFrame } from "@odoo/hoot-mock";
import { unformat } from "./_helpers/format";

class Test extends models.Model {
    name = fields.Char();
    txt = fields.Html();
    _records = [
        { id: 1, name: "Test", txt: "<p>text</p>".repeat(50) },
        {
            id: 2,
            name: "Test",
            txt: unformat(`
                <table><tbody>
                    <tr>
                        <td><p>cell 0</p></td>
                        <td><p>cell 1</p></td>
                    </tr>
                </tbody></table>
                ${"<p>text</p>".repeat(50)}`),
        },
    ];
}

defineModels([Test]);

test.tags("desktop")("Toolbar should not overflow scroll container", async () => {
    const top = (elementOrRange) => elementOrRange.getBoundingClientRect().top;
    const bottom = (elementOrRange) => elementOrRange.getBoundingClientRect().bottom;

    await mountView({
        type: "form",
        resId: 1,
        resModel: "test",
        arch: `
            <form>
                <field name="name"/>
                <field name="txt" widget="html"/>
            </form>`,
    });

    const scrollableElement = queryOne(".o_content");
    const editable = queryOne(".odoo-editor-editable");

    // Select a paragraph in the middle of the text
    const fifthParagraph = editable.children[5];
    setSelection({
        anchorNode: fifthParagraph,
        anchorOffset: 0,
        focusNode: fifthParagraph,
        focusOffset: 1,
    });
    const range = document.getSelection().getRangeAt(0);

    const toolbar = await waitFor(".o-we-toolbar");

    // Toolbar should be above the selection
    expect(bottom(toolbar)).toBeLessThan(top(range));

    // Scroll down to bring the toolbar close to the top
    let scrollStep = top(toolbar) - top(scrollableElement);
    scrollableElement.scrollTop += scrollStep;
    await animationFrame();

    // Toolbar should be below the selection
    expect(top(toolbar)).toBeGreaterThan(bottom(range));

    // Toolbar should not overflow the scroll container
    expect(top(toolbar)).toBeGreaterThan(top(scrollableElement));

    // Scroll down to make the toolbar overflow the scroll container
    scrollStep = top(toolbar) - top(scrollableElement);
    scrollableElement.scrollTop += scrollStep;
    await animationFrame();

    // Toolbar should be invisible
    expect(toolbar).not.toBeVisible();

    // Scroll up to make the toolbar visible again
    scrollableElement.scrollTop -= scrollStep;
    await animationFrame();

    expect(toolbar).toBeVisible();
});

test.tags("desktop")(
    "Table column control should always be displayed on top of the table",
    async () => {
        const top = (el) => el.getBoundingClientRect().top;
        const bottom = (el) => el.getBoundingClientRect().bottom;

        await mountView({
            type: "form",
            resId: 2,
            resModel: "test",
            arch: `
            <form>
                <field name="name"/>
                <field name="txt" widget="html"/>
            </form>`,
        });

        const scrollableElement = queryOne(".o_content");
        const table = queryOne(".odoo-editor-editable table");
        hover(".odoo-editor-editable td");
        const columnControl = await waitFor(".o-we-table-menu[data-type='column']");

        // Table column control displayed on hover should be above the table
        expect(bottom(columnControl)).toBeLessThan(top(table));

        // Scroll down so that the table is close to the top
        const distanceToTop = top(table) - top(scrollableElement);
        scrollableElement.scrollTop += distanceToTop;
        await animationFrame();

        hover(".odoo-editor-editable td");
        await animationFrame();

        // Table control should not be displayed (it should not overflow the scroll
        // container, nor be placed below the first row).
        expect(queryAll(".o-we-table-menu[data-type='column']")).toHaveCount(0);
    }
);

test.tags("desktop")("Table menu should close on scroll", async () => {
    await mountView({
        type: "form",
        resId: 2,
        resModel: "test",
        arch: `
            <form>
                <field name="name"/>
                <field name="txt" widget="html"/>
            </form>`,
    });

    const scrollableElement = queryOne(".o_content");

    hover(".odoo-editor-editable td");
    const columnControl = await waitFor(".o-we-table-menu[data-type='column']");
    click(columnControl);
    await animationFrame();

    // Column menu should be displayed.
    expect(".o-dropdown--menu").toBeVisible();

    // Scroll down
    scrollableElement.scrollTop += 10;
    await waitForNone(".o-dropdown--menu");

    // Column menu should not be visible.
    expect(".o-dropdown--menu").not.toBeVisible();
});

