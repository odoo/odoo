import { expect, test } from '@odoo/hoot';
import { queryAllTexts } from '@odoo/hoot-dom';
import { saleManagementModels } from "@sale_management/../tests/sale_management_test_helpers";
import {
    clickCancel,
    clickSave,
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from '@web/../tests/web_test_helpers';

class AccountFiscalPosition extends models.ServerModel {
    _name = "account.fiscal.position";

    _records = [
        {
            id: 1,
            name: "Test Fiscal Position",
        },
    ];
}

class UomUom extends models.ServerModel {
    _name = "uom.uom";

    _records = [
        { id: 1, name: "Units", factor: 1, parent_path: "1/" },
        { id: 2, name: "Dozens", factor: 12, parent_path: "1/2/" },
        { id: 3, name: "kg", factor: 1, parent_path: "3/" },
    ];
}

class SaleOrderLine extends saleManagementModels.SaleOrderLine {
    // for skipping tax setup required for prices computation to run correctly
    price_unit = fields.Float({ default: 3.00 });
    price_total = fields.Float({ default: 3.00 });
    price_subtotal = fields.Float({ default: 3.50 });
    product_uom_qty = fields.Float({ default: 1.00 });
    section_qty = fields.Float({ default: 0.00 });

    _records = [
        { id: 1, name: "r1", sequence: 1, product_id: 1 },
        { id: 2, name: "r2", sequence: 2, product_id: 1 },
        {
            id: 3,
            name: "Sec1",
            sequence: 3,
            display_type: 'line_section',
            section_qty: 1,
            section_uom_id: 1,
            product_uom_qty: 0,
            price_unit: 0,
            price_total: 0,
            price_subtotal: 0,
            collapse_prices: true,
        },
        {
            id: 4,
            name: "Sec2",
            sequence: 4,
            display_type: 'line_section',
            section_qty: 1,
            section_uom_id: 1,
            product_uom_qty: 0,
            price_unit: 0,
            price_total: 0,
            price_subtotal: 0,
            collapse_composition: true,
        },
        {
            id: 5,
            name: "Sec3",
            sequence: 5,
            display_type: 'line_section',
            section_qty: 1,
            section_uom_id: 1,
            product_uom_qty: 0,
            price_unit: 0,
            price_total: 0,
            price_subtotal: 0,
        },
        { id: 6, name: "Sec3-r1", sequence: 6, product_id: 1 },
        { id: 7, name: "Sec3-r2", sequence: 7, product_id: 1 },
        {
            id: 8,
            name: "Sec3-sub1",
            sequence: 8,
            display_type: 'line_subsection',
            section_qty: 1,
            section_uom_id: 1,
            product_uom_qty: 0,
            price_unit: 0,
            price_total: 0,
        },
        { id: 9, name: "Sec3-sub1-r1", sequence: 9, product_id: 1 },
        {
            id: 10,
            name: "Sec3-sub2",
            sequence: 10,
            display_type: 'line_subsection',
            section_qty: 1,
            section_uom_id: 1,
            product_uom_qty: 0,
            price_unit: 0,
            price_total: 0,
        },
        { id: 11, name: "Sec3-sub2-r1", sequence: 11, product_id: 1 },
        {
            id: 12,
            name: "Sec4",
            sequence: 12,
            display_type: 'line_section',
            section_qty: 1,
            section_uom_id: 1,
            product_uom_qty: 0,
            price_unit: 0,
            price_total: 0,
            price_subtotal: 0
        },
        { id: 13, name: "Sec4-r1", sequence: 13, product_id: 1 },
        {
            id: 14,
            name: "Sec4-sub1",
            sequence: 14,
            display_type: 'line_subsection',
            section_qty: 1,
            section_uom_id: 1,
            product_uom_qty: 0,
            price_unit: 0,
            price_total: 0,
            collapse_composition: true,
            collapse_prices: true,
        },
        { id: 15, name: "Sec4-sub1-r1", sequence: 15, product_id: 2 },
    ];
}

class SaleOrder extends saleManagementModels.SaleOrder {
    _records = [
        {
            id: 1,
            name: "Optional Sections Sale order",
            order_line: SaleOrderLine._records.map(record => record.id),
            company_id: 1,
            fiscal_position_id: 1,
            currency_id: 1,
        },
    ];
    _views = {
        form: `
            <form js_class="sale_order_form">
                <field name="company_id" invisible="1"/>
                <field name="fiscal_position_id" invisible="1"/>
                <field name="currency_id" invisible="1"/>
                <field
                    name="order_line"
                    widget="sol_o2m"
                    options="{'subsections': True, 'hide_composition': True, 'hide_prices': True}"
                >
                    <list editable="bottom">
                        <control>
                            <create name="add_line_control" string="Add a line"/>
                            <create name="add_section_control" string="Add a section" context="{'default_display_type': 'line_section'}"/>
                            <create name="add_note_control" string="Add a note" context="{'default_display_type': 'line_note'}"/>
                        </control>
                        <field name="sequence" widget="handle"/>
                        <column name="product_and_description">
                            <field name="name" invisible="not display_type"/>
                            <field name="label" invisible="display_type"/>
                        </column>
                        <field name="product_id" invisible="display_type"/>
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
                        <field name="price_unit"/>
                        <field name="price_total"/>
                        <field name="price_subtotal"/>
                        <field name="display_type" column_invisible="1"/>
                        <field name="collapse_composition" column_invisible="1"/>
                        <field name="collapse_prices" column_invisible="1"/>
                        <field name="is_optional" column_invisible="1"/>
                    </list>
                </field>
            </form>
        `,
    };
}

defineModels({
    ...saleManagementModels,
    SaleOrderLine,
    SaleOrder,
    AccountFiscalPosition,
    UomUom,
});

const EXPECTED_LINE_RECORDS = [
    "r1",
    "r2",
    "Sec1",
    "Sec2",
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

test("Can't mark section hidden if optional and vice versa", async () => {
    await mountView({
        type: 'form',
        resModel: 'sale.order',
        resId: 1,
    });

    expect(queryAllTexts(".o_data_row td[name=product_and_description]")).toEqual(
        EXPECTED_LINE_RECORDS
    );

    await contains('.o_data_row:contains(Sec1) .o_list_section_options button').click();
    expect('.o-dropdown-item:contains(Set Optional)').toHaveClass('disabled', {
        message: "Section with hidden prices can't be optional"
    });

    await contains('.o_data_row:contains(Sec2) .o_list_section_options button').click();
    expect('.o-dropdown-item:contains(Set Optional)').toHaveClass('disabled', {
        message: "Hidden section can't be optional"
    });
})

test("Setting section optional should reset some fields", async () => {
    onRpc('web_save', ({ args }) => {
        expect.step('web_save');
        expect(args[1]).toEqual(
            {
                order_line: [
                    [1, 10, { collapse_composition: false, collapse_prices: false }],
                    [1, 8, { collapse_composition: false, collapse_prices: false }],
                    [1, 5, { is_optional: true }],
                    [1, 6, { product_uom_qty: 0, price_total: 0, price_subtotal: 0 }],
                    [1, 7, { product_uom_qty: 0, price_total: 0, price_subtotal: 0 }],
                    [1, 9, { product_uom_qty: 0, price_total: 0, price_subtotal: 0 }],
                    [1, 11, { product_uom_qty: 0, price_total: 0, price_subtotal: 0 }],
                ],
            },
            { message: "Subsections reset collapse_* fields' value and product lines reset qty/price when section becomes optional" }
        );
    });

    await mountView({
        type: 'form',
        resModel: 'sale.order',
        resId: 1,
    });

    expect(queryAllTexts(".o_data_row td[name=product_and_description]")).toEqual(
        EXPECTED_LINE_RECORDS
    );

    await contains('.o_data_row:contains(Sec3-sub2) .o_list_section_options button').click();
    await contains('.o-dropdown-item:contains(Hide Composition)').click();

    await contains('.o_data_row:contains(Sec3-sub1) .o_list_section_options button').click();
    await contains('.o-dropdown-item:contains(Hide Prices)').click();

    await contains('.o_data_row:contains(Sec3) .o_list_section_options button').click();
    await contains('.o-dropdown-item:contains(Set Optional)').click();

    await clickSave();
    await expect.verifySteps(['web_save']);
})

test("Unsetting optional section should reset some fields", async () => {
    SaleOrderLine._records.find(record => record.name === 'Sec3').is_optional = true;
    SaleOrderLine._records.find(record => record.name === 'Sec3-r1').product_uom_qty = 0;
    SaleOrderLine._records.find(record => record.name === 'Sec3-r2').product_uom_qty = 0;
    SaleOrderLine._records.find(record => record.name === 'Sec3-sub1-r1').product_uom_qty = 0;
    // This line should not be reset
    SaleOrderLine._records.find(record => record.name === 'Sec3-sub2-r1').product_uom_qty = 5;

    onRpc('web_save', ({ args }) => {
        expect.step('web_save');
        expect(args[1]).toEqual(
            {
                order_line: [
                    [1, 5, { is_optional: false }],
                    [1, 6, { product_uom_qty: 1 }],
                    [1, 7, { product_uom_qty: 1 }],
                    [1, 9, { product_uom_qty: 1 }],
                    [1, 11, { product_uom_qty: 5 }],
                ],
            },
            { message: "The subsections should reset products lines with 0 quantity with 1 as soon as section becomes non optional" }
        );
    });

    await mountView({
        type: 'form',
        resModel: 'sale.order',
        resId: 1,
    });

    expect(queryAllTexts(".o_data_row td[name=product_and_description]")).toEqual(
        EXPECTED_LINE_RECORDS
    );

    expect('.o_data_row:contains(Sec3-r1)').toHaveClass('text-primary', {
        message: "Line under optional section should be text-primary"
    });
    expect('.o_data_row:contains(Sec3-sub1)').toHaveClass('text-primary', {
        message: "Subsection under optional section should be text-primary"
    });
    expect('.o_data_row:contains(Sec3-sub1-r1)').toHaveClass('text-primary', {
        message: "Line under subsection(which is under optional section) should be text-primary"
    });

    await contains('.o_data_row:contains(Sec3) .o_list_section_options button').click();
    await contains('.o-dropdown-item:contains(Unset Optional)').click();

    await clickSave();
    await expect.verifySteps(['web_save']);
})

test("drag and drop regular line inside optional section resets some fields", async () => {
    SaleOrderLine._records.find(record => record.name === 'Sec3').is_optional = true;
    SaleOrderLine._records.find(record => record.name === 'Sec3-sub2-r1').product_uom_qty = 0;
    SaleOrderLine._records.find(record => record.name === 'Sec3-sub1-r1').product_uom_qty = 1;

    onRpc('web_save', ({ args }) => {
        expect.step('web_save');

        expect(args[1].order_line.find(commands => commands[1] === 13)[2].product_uom_qty).toEqual(  // Sec4-r1
            0,
            { message: "Drag and drop inside optional section should reset product_uom_qty to 0" },
        );
        expect(args[1].order_line.find(commands => commands[1] === 11)[2].product_uom_qty).toEqual(  // Sec3-sub2-r1
            1,
            { message: "Drag and drop line with 0 quantity outside optional section should reset product_uom_qty to 1" },
        );
        expect(args[1].order_line.find(commands => commands[1] === 9)?.[2].product_uom_qty).toEqual(  // Sec3-sub1-r1
            undefined,
            { message: "Drag and drop line with non-zero quantity outside optional section shouldn't reset product_uom_qty" }
        );
    })

    await mountView({
        type: 'form',
        resModel: 'sale.order',
        resId: 1,
    });

    expect(queryAllTexts(".o_data_row td[name=product_and_description]")).toEqual(
        EXPECTED_LINE_RECORDS
    );

    await contains('.o_data_row:contains(Sec4-r1):first .o_row_handle').dragAndDrop('.o_data_row:contains(Sec3-sub2):first');
    await contains('.o_data_row:contains(Sec3-sub2-r1):first .o_row_handle').dragAndDrop('.o_data_row:contains(Sec4-sub1):first');
    await contains('.o_data_row:contains(Sec3-sub1-r1):first .o_row_handle').dragAndDrop('.o_data_row:contains(Sec4-sub1):first');

    await clickSave();
    await expect.verifySteps(['web_save']);
})

test("Moving Optional Sections to include some lines should set quantity to 0", async () => {
    SaleOrderLine._records.find(record => record.name === 'Sec4').is_optional = true;
    // keep sec4-r1's quantity 1 so that we can check that it doesn't reset
    SaleOrderLine._records.find(record => record.name === 'Sec4-sub1-r1').product_uom_qty = 0;
    onRpc('web_save', ({ args }) => {
        expect.step('web_save');

        expect(args[1].order_line.find(commands => commands[1] === 7)[2].product_uom_qty).toEqual(  // Sec3-r2
            0,
            { message: "New lines added to an optional section should have product_uom_qty set to 0" },
        );
        expect(args[1].order_line.find(commands => commands[1] === 9)[2].product_uom_qty).toEqual(  // Sec3-sub1-r1
            0,
            { message: "New lines added to a subsection of an optional section should also have product_uom_qty set to 0" },
        );
        expect(args[1].order_line.find(commands => commands[1] === 13)?.[2].product_uom_qty).toEqual( // Sec4-r1
            undefined,
            { message: "Existing optional lines should keep their current product_uom_qty" }
        );
    });

    await mountView({
        type: 'form',
        resModel: 'sale.order',
        resId: 1,
    });

    expect(queryAllTexts(".o_data_row td[name=product_and_description]")).toEqual(
        EXPECTED_LINE_RECORDS
    );

    await contains('.o_data_row:contains(Sec4):first .o_row_handle').dragAndDrop('.o_data_row:contains(Sec3-r2):first');
    await clickSave();
    await expect.verifySteps(['web_save']);
})

test("Moving Optional Sections to exclude some lines should set quantity to 1", async () => {
    SaleOrderLine._records.find(record => record.name === 'Sec3').is_optional = true;
    SaleOrderLine._records.find(record => record.name === 'Sec3-r1').product_uom_qty = 0;
    SaleOrderLine._records.find(record => record.name === 'Sec3-sub1-r1').product_uom_qty = 0;
    onRpc('web_save', ({ args }) => {
        expect.step('web_save');

        expect(args[1].order_line.find(command => command[1] === 6)[2].product_uom_qty).toEqual(  // Sec3-r1
            1,
            { message: "Non-optional lines should reset product_uom_qty to 1 when it was previously 0." },
        );
        expect(args[1].order_line.find(command => command[1] === 7)?.[2].product_uom_qty).toEqual(  // Sec3-r2
            undefined,
            { message: "Non-optional lines should keep their existing product_uom_qty when it was already non-zero." },
        );
        expect(args[1].order_line.find(command => command[1] === 9)[2].product_uom_qty).toEqual(  // Sec3-sub1-r1
            1,
            { message: "Lines moved out of an optional subsection should reset product_uom_qty to 1 when it was 0." },
        );
        expect(args[1].order_line.find(command => command[1] === 11)?.[2].product_uom_qty).toEqual(  // Sec3-sub2-r1
            undefined,
            { message: "Lines moved out of an optional subsection should keep their existing product_uom_qty when it was already non-zero." },
        );
    });

    await mountView({
        type: 'form',
        resModel: 'sale.order',
        resId: 1,
    });

    expect(queryAllTexts(".o_data_row td[name=product_and_description]")).toEqual(
        EXPECTED_LINE_RECORDS
    );

    await contains('.o_data_row:contains(Sec3):first .o_row_handle').dragAndDrop('.o_data_row:contains(Sec4):first');
    await clickSave();
    await expect.verifySteps(['web_save']);
})

test("Drag and drop optional subsection under hidden section resets its optional state", async () => {
    SaleOrderLine._records[7].is_optional = true;

    onRpc("web_save", ({ args }) => {
        expect.step("web_save");

        expect(args[1].order_line.find((commands) => commands[1] === 8)[2].is_optional).toBe(
            false,
            {
                message: "is_optional should reset to false for subsection Sec3-sub1",
            }
        );
    });

    await mountView({
        type: "form",
        resModel: "sale.order",
        resId: 1,
    });

    expect(queryAllTexts(".o_data_row td[name=product_and_description]")).toEqual(
        EXPECTED_LINE_RECORDS
    );

    await contains(".o_data_row:contains(Sec3-sub1):first .o_row_handle").dragAndDrop(
        ".o_data_row:contains(Sec3):first"
    );

    await clickSave();
    expect.verifySteps(["web_save"]);
});

test.tags("desktop");
test("Selecting a section template should append its section and lines to the order", async () => {
    await mountView({
        type: "form",
        resModel: "sale.order",
        resId: 1,
    });

    await contains("button:contains(Add Section)").click();
    expect(".o_section_templates_dropdown").toBeVisible();

    await contains("span.o-dropdown-item:contains(Section Template 1)").click();
    expect(queryAllTexts(".o_data_row td[name=product_and_description]")).toEqual([
        ...EXPECTED_LINE_RECORDS,
        "Section Template 1",
        "line1",
        "line2",
    ]);
});

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
    await contains(".o_selected_row [name=section_qty] input", { visible: false }).edit("4", { confirm: "blur" });
    await clickSave();

    expect.verifySteps(["batch_onchange_sol", "web_save"]);
});

test("Editing a section's quantity applies the ratio to its lines", async () => {
    onRpc("batch_onchange_sol", ({ args }) => {
        expect.step("batch_onchange_sol");
        const [sectionLinesData] = args;

        expect(Object.keys(sectionLinesData)).toEqual(["13", "14", "15"]);
        for (const lineId of [13, 15]) {
            expect(sectionLinesData[lineId].ids).toEqual([lineId], {
                message: "Saved product lines are sent by id so the server can read their product",
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

test.tags("desktop");
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

test.tags("desktop");
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
        expect(newLineData.changes.product_id).toBe(1, {
            message: "The product of an unsaved line must be sent for the server to recompute it",
        });
        expect(newLineData.changes.product_uom_qty).toBe(3);
        return { [lineIds[1]]: { price_subtotal: 60 } };
    });
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        const newLine = args[1].order_line.find((c) => c[0] === 0)[2];
        expect(newLine.product_id).toBe(1);
        expect(newLine.product_uom_qty).toBe(3);
        expect(newLine.price_subtotal).toBe(60);
    });

    await mountView({ type: "form", resModel: "sale.order", resId: 1 });

    // New lines are appended to the last subsection (Sec4-sub1)
    await contains("button:contains(Add a line)").click();
    await contains(".o_selected_row [name=product_id] input").click();
    await contains(".o-autocomplete--dropdown-item:contains(Test Product)").click();
    await contains(".o_data_row:contains(Sec4-sub1):first [name=product_and_description]").click();
    await contains(".o_selected_row [name=section_qty] input", { visible: false }).edit("3", { confirm: "blur" });
    await clickSave();

    expect.verifySteps(["batch_onchange_sol", "web_save"]);
});

test.tags("desktop");
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
