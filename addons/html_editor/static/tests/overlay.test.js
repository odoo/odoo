import { expect, test } from "@odoo/hoot";
import { setSelection } from "./_helpers/selection";
import { click, hover, queryOne, waitFor, waitForNone } from "@odoo/hoot-dom";
import { contains, defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";
import { animationFrame } from "@odoo/hoot-mock";
import { unformat } from "./_helpers/format";
import { Plugin } from "@html_editor/plugin";
import { Component, onMounted, onWillUnmount, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { setupEditor } from "./_helpers/editor";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";

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

test.tags("desktop");
test("Toolbar should not overflow scroll container", async () => {
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

test.tags("desktop");
test("Table column control should always be displayed on top of the table", async () => {
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
    await hover(".odoo-editor-editable td");
    let columnControl = await waitFor(".o-we-table-menu[data-type='column']");

    // Table column control displayed on hover should be above the table
    expect(bottom(columnControl)).toBeLessThan(top(table));

    // Scroll down so that the table is close to the top
    const distanceToTop = top(table) - top(scrollableElement);
    scrollableElement.scrollTop += distanceToTop;
    await animationFrame();

    await hover(".odoo-editor-editable td");
    columnControl = await waitFor(".o-we-table-menu[data-type='column']");

    // Table column control still above the table,
    // even though the table is close to the top
    // of its container, but it should be hidden
    expect(bottom(columnControl)).toBeLessThan(top(table));
    expect(columnControl).not.toBeVisible();
});

test.tags("desktop");
test("Table menu should close on scroll", async () => {
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

    await hover(".odoo-editor-editable td");
    const columnControl = await waitFor(".o-we-table-menu[data-type='column']");
    await click(columnControl);
    await animationFrame();

    // Column menu should be displayed.
    expect(".o-dropdown--menu").toBeVisible();

    // Scroll down
    scrollableElement.scrollTop += 10;
    await waitForNone(".o-dropdown--menu");

    // Column menu should not be visible.
    expect(".o-dropdown--menu").not.toHaveCount();
});

test.tags("desktop");
test("Table menu should only show on contenteditable true tables", async () => {
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

    // check that table menu is visible
    await hover(".odoo-editor-editable td");
    await waitFor(".o-we-table-menu[data-type='column']");
    expect(".o-we-table-menu[data-type='column']").toBeVisible();

    // hover away set the table as not editable
    await hover(".o_control_panel");
    queryOne("table").setAttribute("contenteditable", "false");

    // chack that table menu is now not visible
    await hover(".odoo-editor-editable td");
    await waitForNone(".o-we-table-menu[data-type='column']");
    expect(".o-we-table-menu[data-type='column']").not.toHaveCount();
});

test("Toolbar should keep stable while extending down the selection", async () => {
    const top = (el) => el.getBoundingClientRect().top;
    const left = (el) => el.getBoundingClientRect().left;

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

    const editable = queryOne(".odoo-editor-editable");

    // Select inner content of a paragraph in the middle of the text
    const fifthParagraph = editable.children[5];
    const textNode = fifthParagraph.firstChild;
    setSelection({
        anchorNode: textNode,
        anchorOffset: 0,
        focusNode: textNode,
        focusOffset: textNode.length,
    });
    const toolbar = await waitFor(".o-we-toolbar");
    const referenceTop = top(toolbar);
    const referenceLeft = left(toolbar);

    const extendSelection = (focusNode, focusOffset) => {
        setSelection({ anchorNode: textNode, anchorOffset: 0, focusNode, focusOffset });
    };

    // Extend the selection to the beginning of the following paragraph. This
    // simulates the selection obtained by moving the mouse while mousedown.
    const sixthParagraph = fifthParagraph.nextElementSibling;
    extendSelection(sixthParagraph, 0);
    await animationFrame();

    // Toolbar should not move
    expect(top(toolbar)).toBe(referenceTop);
    expect(left(toolbar)).toBe(referenceLeft);

    // Extend selection to end of paragraph
    const textNodeSixthParagraph = sixthParagraph.firstChild;
    extendSelection(textNodeSixthParagraph, textNodeSixthParagraph.length);
    await animationFrame();

    // Toolbar should not move
    expect(top(toolbar)).toBe(referenceTop);
    expect(left(toolbar)).toBe(referenceLeft);
});

test("overlay don't close when click on child overlay", async () => {
    class MySubOverlay extends Component {
        static template = xml`<button class="my-suboverlay">Overlay</button>`;
        static props = {};
    }
    class MyOverlay extends Component {
        static template = xml`<div class="my-overlay">Overlay</div>`;
        static props = {};

        setup() {
            const overlayService = useService("overlay");
            let remove;
            onMounted(() => {
                remove = overlayService.add(MySubOverlay, {});
            });
            onWillUnmount(() => remove?.());
        }
    }

    class MyPlugin extends Plugin {
        static id = "my.plugin";
        static dependencies = ["overlay"];
        setup() {
            this.overlay = this.dependencies.overlay.createOverlay(MyOverlay, {});
            this.overlay.open({ target: this.editable });
        }
        destroy() {
            this.overlay.close();
        }
    }

    const { editor } = await setupEditor("<div>edit</div>", {
        config: { Plugins: [...MAIN_PLUGINS, MyPlugin] },
    });
    await waitFor(".my-overlay");
    await contains(".my-suboverlay").click();
    await animationFrame();
    expect(document.activeElement).toBe(queryOne(".my-suboverlay"));
    expect(".my-overlay").toHaveCount(1);
    editor.destroy();
    await animationFrame();

    await setupEditor("<div>edit</div>", {
        config: { Plugins: [...MAIN_PLUGINS, MyPlugin] },
        props: {
            iframe: true,
        },
    });
    await waitFor(".my-overlay");
    await contains(".my-suboverlay").click();
    await animationFrame();
    expect(document.activeElement).toBe(queryOne(".my-suboverlay"));
    expect(".my-overlay").toHaveCount(1);
});
