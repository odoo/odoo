// @ts-check

import { expect, test } from "@odoo/hoot";
import { press, queryAll } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { onRendered, useState } from "@odoo/owl";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    patchWithCleanup,
    webModels,
} from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { registerTemplate } from "@web/core/templates";
import { getRowComponentClass, ListRecordRow } from "@web/views/list/list_record_row";
import { ListRenderer } from "@web/views/list/list_renderer";

class Foo extends models.Model {
    name = fields.Char();
    _records = [
        { id: 1, name: "alpha" },
        { id: 2, name: "beta" },
        { id: 3, name: "gamma" },
    ];
}

const { ResCompany, ResPartner, ResUsers } = webModels;

defineModels([Foo, ResCompany, ResPartner, ResUsers]);

registerTemplate(
    "test_list_record_row.RecordRow",
    "/web/static/tests/views/list/list_record_row.test.js",
    `
    <t t-name="test_list_record_row.RecordRow"
       t-inherit="web.ListRenderer.RecordRow"
       t-inherit-mode="primary">
        <xpath expr="//tr" position="attributes">
            <attribute name="t-att-data-label">api.rowLabel(record)</attribute>
            <attribute name="t-att-data-highlight">props.rowState.highlight ? 'on' : 'off'</attribute>
            <attribute name="t-on-click">() => api.noteRow(record)</attribute>
        </xpath>
    </t>`,
);

/** @returns {{ get renderer(): any, rendererRenders: number }} */
function setupCustomRowList() {
    /** @type {{ renderer: any, rendererRenders: number }} */
    const captured = { renderer: null, rendererRenders: 0 };
    const listView = registry.category("views").get("list");
    class CustomListRenderer extends listView.Renderer {
        static recordRowTemplate = "test_list_record_row.RecordRow";
        setup() {
            super.setup();
            this.rowState = useState({ highlight: false });
            captured.renderer = this;
            onRendered(() => captured.rendererRenders++);
        }
        /** @param {any} record */
        rowLabel(record) {
            return `label:${record.data.name}`;
        }

        /** @param {any} record */
        noteRow(record) {
            this.notedRecord = record;
        }
        buildRowApi() {
            return {
                ...super.buildRowApi(),
                rowLabel: (/** @type {any} */ record) => this.rowLabel(record),
                noteRow: (/** @type {any} */ record) =>
                    this.noteRow(this.resolveRowRecord(record)),
            };
        }

        /**
         * @param {any} record
         * @param {any} group
         * @param {any} groupId
         */
        getRowProps(record, group, groupId) {
            return {
                ...super.getRowProps(record, group, groupId),
                rowState: this.rowState,
            };
        }
    }
    registry
        .category("views")
        .add(
            "custom_row_list",
            { ...listView, Renderer: CustomListRenderer },
            { force: true },
        );
    return captured;
}

const CUSTOM_ROW_ARCH = `<list js_class="custom_row_list"><field name="name"/></list>`;

test.tags("desktop");
test("api members dispatch on the renderer with the row's record (C1/C4)", async () => {
    setupCustomRowList();
    await mountView({ resModel: "foo", type: "list", arch: CUSTOM_ROW_ARCH });

    const rows = queryAll(".o_data_row");
    expect(rows.map((/** @type {any} */ row) => row.dataset.label)).toEqual([
        "label:alpha",
        "label:beta",
        "label:gamma",
    ]);
    expect(".o_data_row .o_data_cell[name='name']").toHaveCount(3);
});

registerTemplate(
    "test_list_record_row.WidenedRow",
    "/web/static/tests/views/list/list_record_row.test.js",
    `
    <t t-name="test_list_record_row.WidenedRow"
       t-inherit="web.ListRenderer.RecordRow"
       t-inherit-mode="primary">
        <xpath expr="//td[1]" position="replace">
            <td class="o_list_record_selector">
                <CheckBox onChange.bind="(selected) => api.toggleRecordSelection(selected, record)"/>
            </td>
        </xpath>
    </t>`,
);

test.tags("desktop");
test("a row handler forwards every argument, so a renderer may widen its signature", async () => {
    // the shape account_online_synchronization's duplicate-transaction list
    // takes: the renderer's toggleRecordSelection(selected, record) is called
    // from its row template with both arguments
    /** @type {any[]} */
    const calls = [];
    const listView = registry.category("views").get("list");
    class WidenedListRenderer extends listView.Renderer {
        static recordRowTemplate = "test_list_record_row.WidenedRow";
        get hasSelectors() {
            return true;
        }
        /**
         * @param {boolean} selected
         * @param {any} record
         */
        toggleRecordSelection(selected, record) {
            calls.push([selected, record?.data.name]);
        }
    }
    registry
        .category("views")
        .add(
            "widened_row_list",
            { ...listView, Renderer: WidenedListRenderer },
            { force: true },
        );
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list js_class="widened_row_list"><field name="name"/></list>`,
    });
    await contains(".o_data_row:eq(1) .o_list_record_selector input").click();
    expect(calls).toEqual([[true, "beta"]]);
});

test.tags("desktop");
test("action callbacks resolve the record to the renderer's context (C2)", async () => {
    const captured = setupCustomRowList();
    await mountView({ resModel: "foo", type: "list", arch: CUSTOM_ROW_ARCH });

    const secondRow = queryAll(".o_data_row")[1];
    await contains(secondRow.querySelector(".o_data_cell")).click();
    expect(captured.renderer.notedRecord.id).toBe(secondRow.dataset.id);
    expect(captured.renderer.notedRecord).toBe(captured.renderer.props.list.records[1]);
});

test.tags("desktop");
test("getRowProps state re-renders rows without a renderer render (C3)", async () => {
    const captured = setupCustomRowList();
    await mountView({ resModel: "foo", type: "list", arch: CUSTOM_ROW_ARCH });

    const rows = queryAll(".o_data_row");
    expect(rows.map((/** @type {any} */ row) => row.dataset.highlight)).toEqual([
        "off",
        "off",
        "off",
    ]);
    const rendererRendersBefore = captured.rendererRenders;

    captured.renderer.rowState.highlight = true;
    await animationFrame();
    expect(rows.map((/** @type {any} */ row) => row.dataset.highlight)).toEqual([
        "on",
        "on",
        "on",
    ]);
    expect(captured.rendererRenders).toBe(rendererRendersBefore);
});

test("row component class components are a live view over the renderer's (C5)", () => {
    const TestRenderer = /** @type {any} */ (class extends ListRenderer {});
    TestRenderer.components = { ...ListRenderer.components };
    const RowClass = /** @type {any} */ (getRowComponentClass(TestRenderer));
    expect(RowClass.components).toBe(TestRenderer.components);

    class LateComponent {}
    TestRenderer.components = { ...TestRenderer.components, LateComponent };
    expect(RowClass.components.LateComponent).toBe(LateComponent);
});

test("record, group and groupId come from the row's own props (C7)", () => {
    const get = (/** @type {string} */ name) =>
        /** @type {any} */ (
            Object.getOwnPropertyDescriptor(ListRecordRow.prototype, name)
        ).get;
    const record = { id: 5 };
    const group = { id: "group-7" };
    const row = { props: { record, group, groupId: "group-7" } };
    expect(get("record").call(row)).toBe(record);
    expect(get("group").call(row)).toBe(group);
    expect(get("groupId").call(row)).toBe("group-7");
});

test.tags("desktop");
test("a record data change re-renders that row standalone (C8)", async () => {
    /** @type {any[]} */
    const rowRenders = [];
    patchWithCleanup(ListRecordRow.prototype, {
        setup() {
            super.setup();
            onRendered(() =>
                rowRenders.push(/** @type {any} */ (this).props.record.resId),
            );
        },
    });
    const captured = setupCustomRowList();
    await mountView({ resModel: "foo", type: "list", arch: CUSTOM_ROW_ARCH });
    rowRenders.length = 0;

    const record = captured.renderer.props.list.records[1];
    await record.update({ name: "beta-prime" });
    await animationFrame();

    expect(rowRenders).toEqual([2]);
    expect(
        queryAll(".o_data_row .o_data_cell").map(
            (/** @type {any} */ el) => el.textContent,
        ),
    ).toEqual(["alpha", "beta-prime", "gamma"]);
});

test.tags("desktop");
test("getRowRecords decides the rows of the template, the grid state and keyboard navigation alike", async () => {
    /** @type {any} */
    let renderer = null;
    const listView = registry.category("views").get("list");
    class FilteringListRenderer extends listView.Renderer {
        setup() {
            super.setup();
            this.hidden = useState({ names: [] });
            renderer = this;
        }
        /** @param {any} list */
        getRowRecords(list) {
            return super
                .getRowRecords(list)
                .filter((record) => !this.hidden.names.includes(record.data.name));
        }
    }
    registry
        .category("views")
        .add(
            "filtering_list",
            { ...listView, Renderer: FilteringListRenderer },
            { force: true },
        );
    await mountView({
        type: "list",
        resModel: "foo",
        arch: `<list js_class="filtering_list"><field name="name"/></list>`,
    });
    expect(".o_data_row").toHaveCount(3);
    expect(renderer.gridState.rowCount).toBe(3);

    renderer.hidden.names.push("beta");
    await animationFrame();
    expect(
        queryAll(".o_data_row .o_data_cell").map((cell) => cell.textContent),
    ).toEqual(["alpha", "gamma"]);
    expect(renderer.gridState.rowCount).toBe(2);
    expect(renderer.gridState.findRowByRecordId("2")).toBe(undefined);

    await press("ArrowDown");
    await press("ArrowDown");
    await animationFrame();
    expect(".o_data_row:eq(0) .o_list_record_selector input").toBeFocused();
    await press("ArrowDown");
    await animationFrame();
    expect(".o_data_row:eq(1) .o_list_record_selector input").toBeFocused();
    expect(".o_data_row:eq(1) .o_data_cell").toHaveText("gamma", {
        message: "the hidden row is skipped, not landed on",
    });
});
