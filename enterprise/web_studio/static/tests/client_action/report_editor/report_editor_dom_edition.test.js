import { setupEditor } from "@html_editor/../tests/_helpers/editor";
import { getContent } from "@html_editor/../tests/_helpers/selection";
import { before, expect, test } from "@odoo/hoot";
import { hover, queryAll, queryFirst } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { contains } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";

before(() => {
    const services = registry.category("services");
    for (const [name] of services.getEntries()) {
        if (
            name.startsWith("mail.") ||
            name.startsWith("discuss.") ||
            ["bus.connection_alert", "bus.monitoring_service"].includes(name)
        ) {
            services.remove(name);
        }
    }

    const main_components = registry.category("main_components");
    for (const [name] of main_components.getEntries()) {
        if (name.startsWith("mail.") || name.startsWith("discuss.") || name.startsWith("bus.")) {
            main_components.remove(name);
        }
    }
});

import { QWebPlugin } from "@html_editor/others/qweb_plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { QWebTablePlugin } from "@web_studio/client_action/report_editor/report_editor_wysiwyg/qweb_table_plugin";

const REPORT_EDITOR_PLUGINS = [...MAIN_PLUGINS, QWebPlugin, QWebTablePlugin];
const baseConfig = {
    Plugins: REPORT_EDITOR_PLUGINS,
    classList: ["odoo-editor-qweb"],
};

function getEditorOptions() {
    return {
        config: { ...baseConfig },
        props: {
            iframe: true,
            copyCss: true,
        },
    };
}

test("add column", async () => {
    const { editor } = await setupEditor(
        `<div style="width: 100px; margin-top: 50px; margin-left: 50px;">
        <q-table>
            <q-thead>
                <q-tr>
                    <q-th>HEAD1</q-th>
                    <q-th>HEAD2</q-th>
                </q-tr>
            </q-thead>
            <q-tbody>
                <q-tr>
                    <t t-if="true">
                        <q-td>1[]</q-td>
                        <q-td>2</q-td>
                    </t>
                    <t t-else="">
                        <q-td>3</q-td>
                        <q-td>4</q-td>
                    </t>
                </q-tr>
                <q-tr>
                    <q-td>5</q-td>
                    <q-td>6</q-td>
                </q-tr>
            </q-tbody>
        </q-table></div>`,
        getEditorOptions()
    );

    await hover(queryFirst(":iframe q-th"));
    await contains(".o-overlay-container .o-we-table-menu").click();
    await contains(".o-dropdown-item:contains(Insert Right)").click();

    expect(getContent(editor.getElContent().firstElementChild)).toBe(`
        <q-table>
            <q-thead>
                <q-tr>
                    <q-th>HEAD1</q-th><q-th><div><br></div></q-th>
                    <q-th>HEAD2</q-th>
                </q-tr>
            </q-thead>
            <q-tbody>
                <q-tr>
                    <t t-if="true">
                        <q-td>1</q-td><q-td><div><br></div></q-td>
                        <q-td>2</q-td>
                    </t>
                    <t t-else="">
                        <q-td>3</q-td><q-td><div><br></div></q-td>
                        <q-td>4</q-td>
                    </t>
                </q-tr>
                <q-tr>
                    <q-td>5</q-td><q-td><div><br></div></q-td>
                    <q-td>6</q-td>
                </q-tr>
            </q-tbody>
        </q-table>`);
});

test("add column non-matching conditionals", async () => {
    const { editor } = await setupEditor(
        `<div style="width: 100px; margin-top: 50px; margin-left: 50px;">
        <q-table>
            <q-thead>
                <q-tr>
                    <q-th>HEAD1</q-th>
                    <q-th t-if="true">HEAD2</q-th>
                    <q-th t-else="">HEAD3</q-th>
                    <q-th>HEAD4</q-th>
                </q-tr>
            </q-thead>
            <q-tbody>
                <t t-if="true">
                    <q-tr>
                        <q-td>1</q-td>
                        <q-td>2</q-td>
                        <q-td>4</q-td>
                    </q-tr>
                </t>
                <t t-else="">
                    <q-tr>
                        <q-td>1</q-td>
                        <q-td>3</q-td>
                        <q-td>4</q-td>
                    </q-tr>
                </t>
            </q-tbody>
        </q-table></div>`,
        getEditorOptions()
    );

    await hover(queryFirst(":iframe q-th:last-child"));
    await contains(".o-overlay-container .o-we-table-menu").click();
    await contains(".o-dropdown-item:contains(Insert Right)").click();

    expect(getContent(editor.getElContent().firstElementChild)).toBe(`
        <q-table>
            <q-thead>
                <q-tr>
                    <q-th>HEAD1</q-th>
                    <q-th t-if="true">HEAD2</q-th>
                    <q-th t-else="">HEAD3</q-th>
                    <q-th>HEAD4</q-th><q-th><div><br></div></q-th>
                </q-tr>
            </q-thead>
            <q-tbody>
                <t t-if="true">
                    <q-tr>
                        <q-td>1</q-td>
                        <q-td>2</q-td>
                        <q-td>4</q-td><q-td><div><br></div></q-td>
                    </q-tr>
                </t>
                <t t-else="">
                    <q-tr>
                        <q-td>1</q-td>
                        <q-td>3</q-td>
                        <q-td>4</q-td><q-td><div><br></div></q-td>
                    </q-tr>
                </t>
            </q-tbody>
        </q-table>`);
});

test("remove column", async () => {
    const { editor } = await setupEditor(
        `<div style="width: 100px; margin-top: 50px; margin-left: 50px;">
        <q-table>
            <q-thead>
                <q-tr>
                    <q-th>HEAD1</q-th>
                    <q-th>HEAD2</q-th>
                </q-tr>
            </q-thead>
            <q-tbody>
                <q-tr>
                    <t t-if="true">
                        <q-td>1[]</q-td>
                        <q-td>2</q-td>
                    </t>
                    <t t-else="">
                        <q-td>3</q-td>
                        <q-td>4</q-td>
                    </t>
                </q-tr>
                <q-tr>
                    <q-td>5</q-td>
                    <q-td>6</q-td>
                </q-tr>
            </q-tbody>
        </q-table></div>`,
        getEditorOptions()
    );
    await hover(queryFirst(":iframe q-th"));
    await contains(".o-overlay-container .o-we-table-menu").click();
    await contains(".o-dropdown-item:contains(Delete)").click();

    const el = editor.getElContent();
    expect(getContent(el.firstElementChild)).toBe(`
        <q-table>
            <q-thead>
                <q-tr>
${"                    "}
                    <q-th>HEAD2</q-th>
                </q-tr>
            </q-thead>
            <q-tbody>
                <q-tr>
                    <t t-if="true">
${"                        "}
                        <q-td>2</q-td>
                    </t>
                    <t t-else="">
${"                        "}
                        <q-td>4</q-td>
                    </t>
                </q-tr>
                <q-tr>
${"                    "}
                    <q-td>6</q-td>
                </q-tr>
            </q-tbody>
        </q-table>`);
});

test("remove column colspan", async () => {
    const { editor, el } = await setupEditor(
        `<div style="width: 100px; margin-top: 50px; margin-left: 50px;">
        <q-table>
            <q-thead>
                <q-tr>
                    <q-th>HEAD1</q-th>
                    <q-th>HEAD2</q-th>
                    <q-th>HEAD3</q-th>
                </q-tr>
            </q-thead>
            <q-tbody>
                <q-tr>
                    <t t-if="true">
                        <q-td colspan="2">1[]</q-td>
                        <q-td>2</q-td>
                    </t>
                    <t t-else="">
                        <q-td colspan="2">3</q-td>
                        <q-td>4</q-td>
                    </t>
                </q-tr>
                <q-tr>
                    <q-td>5</q-td>
                    <q-td colspan="2">6</q-td>
                </q-tr>
            </q-tbody>
        </q-table></div>`,
        getEditorOptions()
    );

    expect(getContent(el.firstElementChild)).toBe(`
        <q-table class="oe_unbreakable" style="--q-table-col-count: 3;">
            <q-thead class="oe_unbreakable">
                <q-tr class="oe_unbreakable">
                    <q-th class="oe_unbreakable">HEAD1</q-th>
                    <q-th class="oe_unbreakable">HEAD2</q-th>
                    <q-th class="oe_unbreakable">HEAD3</q-th>
                </q-tr>
            </q-thead>
            <q-tbody class="oe_unbreakable">
                <q-tr class="oe_unbreakable">
                    <t t-if="true" data-oe-t-inline="true" data-oe-t-group="0" data-oe-t-selectable="true" data-oe-t-group-active="true">
                        <q-td colspan="2" class="oe_unbreakable" style="--q-cell-col-size: 2;">1[]</q-td>
                        <q-td class="oe_unbreakable">2</q-td>
                    </t>
                    <t t-else="" data-oe-t-inline="true" data-oe-t-selectable="true" data-oe-t-group="0">
                        <q-td colspan="2" class="oe_unbreakable" style="--q-cell-col-size: 2;">3</q-td>
                        <q-td class="oe_unbreakable">4</q-td>
                    </t>
                </q-tr>
                <q-tr class="oe_unbreakable">
                    <q-td class="oe_unbreakable">5</q-td>
                    <q-td colspan="2" class="oe_unbreakable" style="--q-cell-col-size: 2;">6</q-td>
                </q-tr>
            </q-tbody>
        </q-table>`);

    await hover(queryAll(":iframe q-th")[1]);
    await contains(".o-overlay-container .o-we-table-menu").click();
    await contains(".o-dropdown-item:contains(Delete)").click();

    const cleanedEl = editor.getElContent();
    expect(getContent(cleanedEl.firstElementChild)).toBe(`
        <q-table>
            <q-thead>
                <q-tr>
                    <q-th>HEAD1</q-th>
${"                    "}
                    <q-th>HEAD3</q-th>
                </q-tr>
            </q-thead>
            <q-tbody>
                <q-tr>
                    <t t-if="true">
                        <q-td>1</q-td>
                        <q-td>2</q-td>
                    </t>
                    <t t-else="">
                        <q-td>3</q-td>
                        <q-td>4</q-td>
                    </t>
                </q-tr>
                <q-tr>
                    <q-td>5</q-td>
                    <q-td>6</q-td>
                </q-tr>
            </q-tbody>
        </q-table>`);
});

test("move outside table menu must remove it if the menu is close", async () => {
    await setupEditor(
        `<div style="width: 100px; margin-top: 50px; margin-left: 50px;">
        <q-table>
            <q-thead>
                <q-tr>
                    <q-th>HEAD1</q-th>
                    <q-th>HEAD2</q-th>
                </q-tr>
            </q-thead>
            <q-tbody>
                <q-tr>
                    <t t-if="true">
                        <q-td>1[]</q-td>
                        <q-td>2</q-td>
                    </t>
                    <t t-else="">
                        <q-td>3</q-td>
                        <q-td>4</q-td>
                    </t>
                </q-tr>
                <q-tr>
                    <q-td>5</q-td>
                    <q-td>6</q-td>
                </q-tr>
            </q-tbody>
        </q-table></div>`,
        getEditorOptions()
    );

    await hover(queryAll(":iframe q-th")[1]);
    await animationFrame();
    expect(".o-overlay-container .o-we-table-menu").toHaveCount(1);

    await hover(":iframe q-table");
    await animationFrame();
    expect(".o-overlay-container .o-we-table-menu").toHaveCount(0);
});

test("move outside table menu shouldn't remove it if the menu is close, we should click to close it", async () => {
    await setupEditor(
        `<div style="width: 100px; margin-top: 50px; margin-left: 50px;">
        <q-table>
            <q-thead>
                <q-tr>
                    <q-th>HEAD1</q-th>
                    <q-th>HEAD2</q-th>
                </q-tr>
            </q-thead>
            <q-tbody>
                <q-tr>
                    <t t-if="true">
                        <q-td>1[]</q-td>
                        <q-td>2</q-td>
                    </t>
                    <t t-else="">
                        <q-td>3</q-td>
                        <q-td>4</q-td>
                    </t>
                </q-tr>
                <q-tr>
                    <q-td>5</q-td>
                    <q-td>6</q-td>
                </q-tr>
            </q-tbody>
        </q-table></div>`,
        getEditorOptions()
    );

    await hover(queryAll(":iframe q-th")[1]);
    await animationFrame();
    expect(".o-overlay-container .o-we-table-menu").toHaveCount(1);
    expect(".o-dropdown-item").toHaveCount(0);

    await contains(".o-overlay-container .o-we-table-menu").click();
    expect(".o-overlay-container .o-we-table-menu").toHaveCount(1);
    expect(".o-dropdown-item").toHaveCount(3);

    await hover(":iframe q-table");
    await animationFrame();
    expect(".o-overlay-container .o-we-table-menu").toHaveCount(1);
    expect(".o-dropdown-item").toHaveCount(3);

    await contains(":iframe q-table").click();
    await animationFrame();
    expect(".o-overlay-container .o-we-table-menu").toHaveCount(0);
    expect(".o-dropdown-item").toHaveCount(0);
});
