import { describe, expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import {
    clickCancel,
    clickSave,
    contains,
    defineModels,
    fields,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { saleModels } from "./sale_test_helpers";

class SaleOrderLine extends saleModels.SaleOrderLine {
    // for skipping tax setup required for prices computation to run correctly
    price_subtotal = fields.Float({ default: 3.5 });
    product_uom_qty = fields.Float({ default: 1 });

    _records = [
        { id: 1, name: "r1", sequence: 1 },
        { id: 2, name: "r2", sequence: 2 },
        {
            id: 3,
            name: "Sec1",
            sequence: 3,
            display_type: "line_section",
            product_uom_qty: 0,
            price_subtotal: 0,
        },
        {
            id: 5,
            name: "Sec3",
            sequence: 5,
            display_type: "line_section",
            product_uom_qty: 0,
            price_subtotal: 0,
        },
        { id: 6, name: "Sec3-r1", sequence: 6 },
        { id: 7, name: "Sec3-r2", sequence: 7 },
        {
            id: 8,
            name: "Sec3-sub1",
            sequence: 8,
            display_type: "line_subsection",
            product_uom_qty: 0,
            price_subtotal: 0,
        },
        { id: 9, name: "Sec3-sub1-r1", sequence: 9 },
        {
            id: 10,
            name: "Sec3-sub2",
            sequence: 10,
            display_type: "line_subsection",
            product_uom_qty: 0,
            price_subtotal: 0,
        },
        { id: 11, name: "Sec3-sub2-r1", sequence: 11 },
        {
            id: 12,
            name: "Sec4",
            sequence: 12,
            display_type: "line_section",
            product_uom_qty: 0,
            price_subtotal: 0,
        },
        { id: 13, name: "Sec4-r1", sequence: 13 },
        {
            id: 14,
            name: "Sec4-sub1",
            sequence: 14,
            display_type: "line_subsection",
            product_uom_qty: 0,
            price_subtotal: 0,
        },
        { id: 15, name: "Sec4-sub1-r1", sequence: 15 },
    ];
}

class SaleOrder extends saleModels.SaleOrder {
    _records = [
        {
            id: 1,
            name: "Sections Sale order",
            order_line: SaleOrderLine._records.map((record) => record.id),
        },
    ];
    _views = {
        form: `
            <form js_class="sale_order_form">
                <field name="order_line" widget="sol_o2m" options="{'subsections': True}">
                    <list editable="bottom">
                        <control>
                            <create name="add_line_control" string="Add a line"/>
                        </control>
                        <field name="sequence" widget="handle"/>
                        <column name="product_and_description">
                            <field name="name" invisible="not display_type"/>
                            <field name="label" invisible="display_type"/>
                        </column>
                        <column name="sol_qty">
                            <field name="product_uom_qty" invisible="display_type"/>
                            <field
                                name="section_qty"
                                invisible="display_type not in ('line_section', 'line_subsection')"
                            />
                        </column>
                        <column name="sol_uom">
                            <field name="product_uom_id" invisible="display_type"/>
                            <field
                                name="section_uom_id"
                                invisible="display_type not in ('line_section', 'line_subsection')"
                            />
                        </column>
                        <field name="price_subtotal"/>
                        <field name="display_type" column_invisible="1"/>
                    </list>
                </field>
            </form>
        `,
    };
}

defineModels({ ...saleModels, SaleOrderLine, SaleOrder });

describe.current.tags("desktop");

const EXPECTED_LINE_RECORDS = [
    "r1",
    "r2",
    "Sec1",
    "Sec3",
        "Sec3-r1",
        "Sec3-r2",
        "Sec3-sub1",
            "Sec3-sub1-r1",
        "Sec3-sub2",
            "Sec3-sub2-r1",
    "Sec4",
        "Sec4-r1",
        "Sec4-sub1",
            "Sec4-sub1-r1",
];

test("Editing a subsection's quantity applies the ratio to its line and recomputes its price", async () => {
    SaleOrderLine._records.find(record => record.name === "Sec3-sub2").section_qty = 2;
    SaleOrderLine._records.find(record => record.name === "Sec3-sub2-r1").product_uom_qty = 3;

    onRpc("batch_onchange_sol", ({ args }) => {
        expect.step("batch_onchange_sol");
        const [sectionLinesData] = args;

        expect(Object.keys(sectionLinesData)).toEqual(["11"], {
            message: "Only the subsection's own line should be part of the batch onchange call",
        });
        expect(sectionLinesData[11].changes.product_uom_qty).toEqual(6, {
            message: "Sec3-sub2-r1's quantity should be doubled (ratio 4/2 applied to the subsection)",
        });

        return { 11: { price_subtotal: 42 } };
    });

    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        const commands = args[1].order_line;

        expect(commands.find(c => c[1] === 10)[2]).toEqual({ section_qty: 4 }, {
            message: "The subsection's own quantity change should be saved",
        });
        expect(commands.find(c => c[1] === 11)[2]).toEqual({ product_uom_qty: 6, price_subtotal: 42 }, {
            message: "Its line's quantity and recomputed price should both be saved",
        });
    });

    await mountView({
        type: "form",
        resModel: "sale.order",
        resId: 1,
    });

    expect(queryAllTexts(".o_data_row td[name=product_and_description]")).toEqual(
        EXPECTED_LINE_RECORDS
    );

    await contains(".o_data_row:contains(Sec3-sub2):first [name=product_and_description]").click();
    await contains(".o_selected_row [name=section_qty] input", { visible: false }).edit("4");
    await clickSave();

    expect.verifySteps(["batch_onchange_sol", "web_save"]);
});

test("Changing a section's UoM marks the order as dirty and applies the factor to its lines", async () => {
    onRpc("batch_onchange_sol", () => ({}));
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        const commands = args[1].order_line;

        expect(commands.find((c) => c[1] === 10)[2]).toEqual({ section_uom_id: 2 });
        expect(commands.find((c) => c[1] === 11)[2]).toEqual({ product_uom_qty: 12 });
    });

    await mountView({
        type: "form",
        resModel: "sale.order",
        resId: 1,
    });

    await contains(".o_data_row:contains(Sec3-sub2):first [name=product_and_description]").click();
    await contains(".o_selected_row [name=section_uom_id] input", { visible: false }).click();
    await contains(".o-autocomplete--dropdown-item:contains(Dozens)").click();

    expect(".o_form_button_save").toBeVisible({
        message: "The order should be dirty after changing the section's UoM",
    });
    await clickSave();

    expect.verifySteps(["web_save"]);
});

test("Editing a section's quantity applies the ratio to its lines", async () => {
    onRpc("batch_onchange_sol", ({ args }) => {
        expect.step("batch_onchange_sol");
        const [sectionLinesData] = args;

        expect(Object.keys(sectionLinesData)).toEqual(["13", "14", "15"]);
        for (const lineId of [13, 15]) {
            expect(sectionLinesData[lineId].ids).toEqual([lineId], {
                message: "Saved lines are sent by id",
            });
            expect(sectionLinesData[lineId].changes.product_uom_qty).toBe(2);
        }
        // the server recomputes the prices of the product lines
        return { 13: { price_subtotal: 40 }, 15: { price_subtotal: 100 } };
    });
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args[1].order_line.sort((c1, c2) => c1[1] - c2[1])).toEqual([
            [1, 12, { section_qty: 2 }],
            [1, 13, { product_uom_qty: 2, price_subtotal: 40 }],
            [1, 14, { section_qty: 2 }],
            [1, 15, { product_uom_qty: 2, price_subtotal: 100 }],
        ]);
    });

    await mountView({ type: "form", resModel: "sale.order", resId: 1 });

    await contains(".o_data_row:contains(Sec4):first [name=product_and_description]").click();
    await contains(".o_selected_row [name=section_qty] input", { visible: false }).edit("2", { confirm: "blur" });
    await clickSave();

    expect.verifySteps(["batch_onchange_sol", "web_save"]);
});

test("Changing a section's UoM applies the factor to its lines", async () => {
    onRpc("batch_onchange_sol", ({ args }) => {
        expect.step("batch_onchange_sol");
        const [sectionLinesData] = args;

        expect(sectionLinesData[13].changes.product_uom_qty).toBe(12);
        expect(sectionLinesData[15].changes.product_uom_qty).toBe(12);
        return { 13: { price_subtotal: 240 }, 15: { price_subtotal: 600 } };
    });

    await mountView({ type: "form", resModel: "sale.order", resId: 1 });

    await contains(".o_data_row:contains(Sec4):first [name=product_and_description]").click();
    await contains(".o_selected_row [name=section_uom_id] input", { visible: false }).click();
    await contains(".o-autocomplete--dropdown-item:contains(Dozens)").click();

    expect.verifySteps(["batch_onchange_sol"]);
    expect(".o_data_row:contains(Sec4-r1) td[name=sol_qty]").toHaveText("12.00");
    expect(".o_data_row:contains(Sec4-r1) td[name=price_subtotal]").toHaveText("240.00");
    expect(".o_data_row:contains(Sec4-sub1):first td[name=sol_qty]").toHaveText("12.00");
    expect(".o_data_row:contains(Sec4-sub1-r1) td[name=sol_qty]").toHaveText("12.00");
    expect(".o_data_row:contains(Sec4-sub1-r1) td[name=price_subtotal]").toHaveText("600.00");
});

test("Notes inside a section keep their values when the section's quantity changes", async () => {
    SaleOrderLine._records.push({
        id: 16,
        name: "Sec3-note",
        sequence: 7,
        display_type: "line_note",
        product_uom_qty: 0,
        price_unit: 0,
        price_total: 0,
        price_subtotal: 0,
    });

    onRpc("batch_onchange_sol", ({ args }) => {
        expect.step("batch_onchange_sol");
        expect(Object.keys(args[0])).toEqual(["6", "7", "8", "9", "10", "11"], {
            message: "Sec3-note (16) shouldn't be part of the batch onchange call",
        });
        return {};
    });

    await mountView({ type: "form", resModel: "sale.order", resId: 1 });

    await contains(".o_data_row:contains(Sec3):first [name=product_and_description]").click();
    await contains(".o_selected_row [name=section_qty] input", { visible: false }).edit("2", { confirm: "blur" });

    expect.verifySteps(["batch_onchange_sol"]);
});

test("Editing the quantity of a section without lines only updates the section", async () => {
    onRpc("batch_onchange_sol", () => expect.step("batch_onchange_sol"));
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args[1].order_line).toEqual([[1, 3, { section_qty: 2 }]]);
    });

    await mountView({ type: "form", resModel: "sale.order", resId: 1 });
    expect.verifySteps([]);

    await contains(".o_data_row:contains(Sec1):first [name=product_and_description]").click();
    await contains(".o_selected_row [name=section_qty] input", { visible: false }).edit("2", { confirm: "blur" });
    await clickSave();

    expect.verifySteps(["web_save"]);
});

test("Editing a section's quantity also applies the ratio to unsaved lines", async () => {
    onRpc("batch_onchange_sol", ({ args }) => {
        expect.step("batch_onchange_sol");
        const [sectionLinesData] = args;
        const lineIds = Object.keys(sectionLinesData);

        expect(lineIds).toHaveLength(2);
        expect(lineIds[0]).toBe("15");
        expect(lineIds[1]).toMatch(/^virtual_/);
        const newLineData = sectionLinesData[lineIds[1]];
        expect(newLineData.ids).toEqual([], {
            message: "Unsaved lines have no ids to send to the server",
        });
        expect(newLineData.changes.label).toBe("New line", {
            message: "The unsaved values of a new line must be sent for the server to recompute it",
        });
        expect(newLineData.changes.product_uom_qty).toBe(3);
        return { [lineIds[1]]: { price_subtotal: 60 } };
    });
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        const newLine = args[1].order_line.find((c) => c[0] === 0)[2];
        expect(newLine.label).toBe("New line");
        expect(newLine.product_uom_qty).toBe(3);
        expect(newLine.price_subtotal).toBe(60);
    });

    await mountView({ type: "form", resModel: "sale.order", resId: 1 });

    // New lines are appended to the last subsection (Sec4-sub1)
    await contains("button:contains(Add a line)").click();
    await contains(".o_selected_row [name=label] textarea").edit("New line", { confirm: false });
    await contains(".o_data_row:contains(Sec4-sub1):first [name=product_and_description]").click();
    await contains(".o_selected_row [name=section_qty] input", { visible: false }).edit("3", { confirm: "blur" });
    await clickSave();

    expect.verifySteps(["batch_onchange_sol", "web_save"]);
});

test("Changing a section's UoM to an incompatible one doesn't change its lines", async () => {
    onRpc("batch_onchange_sol", () => expect.step("batch_onchange_sol"));
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args[1].order_line).toEqual([[1, 10, { section_uom_id: 3 }]]);
    });

    await mountView({ type: "form", resModel: "sale.order", resId: 1 });

    await contains(".o_data_row:contains(Sec3-sub2):first [name=product_and_description]").click();
    await contains(".o_selected_row [name=section_uom_id] input", { visible: false }).click();
    await contains(".o-autocomplete--dropdown-item:contains(kg)").click();
    await clickSave();

    expect.verifySteps(["web_save"]);
});

test("Discarding a section's quantity change restores its lines", async () => {
    onRpc("batch_onchange_sol", () => {
        expect.step("batch_onchange_sol");
        return {};
    });
    onRpc("web_save", () => expect.step("web_save"));

    await mountView({ type: "form", resModel: "sale.order", resId: 1 });

    await contains(".o_data_row:contains(Sec3-sub2):first [name=product_and_description]").click();
    await contains(".o_selected_row [name=section_qty] input", { visible: false }).edit("4", { confirm: "blur" });
    expect.verifySteps(["batch_onchange_sol"]);
    expect(".o_data_row:contains(Sec3-sub2-r1) td[name=sol_qty]").toHaveText("4.00");

    await clickCancel();

    expect(".o_data_row:contains(Sec3-sub2-r1) td[name=sol_qty]").toHaveText("1.00");
    expect(".o_data_row:contains(Sec3-sub2):first td[name=sol_qty]").toHaveText("1.00");
    expect.verifySteps([]);
});
