import { defineMailModels } from '@mail/../tests/mail_test_helpers';
import { expect, test } from '@odoo/hoot';
import { queryAllTexts } from '@odoo/hoot-dom';
import {
    clickSave,
    contains,
    defineModels,
    fields,
    mountView,
    onRpc,
} from '@web/../tests/web_test_helpers';
import { saleModels } from '@sale/../tests/sale_test_helpers';

class SaleOrderLine extends saleModels.SaleOrderLine {
    // for skipping tax setup required for prices computation to run correctly
    price_unit = fields.Float({ default: 3.00 });
    price_total = fields.Float({ default: 3.00 });
    price_subtotal = fields.Float({ default: 3.50 });
    product_uom_qty = fields.Float({ default: 1.00 });

    _records = [
        { id: 1, name: "r1", sequence: 1 },
        { id: 2, name: "r2", sequence: 2 },
        {
            id: 3,
            name: "Sec1",
            sequence: 3,
            display_type: 'line_section',
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
            product_uom_qty: 0,
            price_unit: 0,
            price_total: 0,
            price_subtotal: 0,
        },
        { id: 6, name: "Sec3-r1", sequence: 6 },
        { id: 7, name: "Sec3-r2", sequence: 7 },
        {
            id: 8,
            name: "Sec3-sub1",
            sequence: 8,
            display_type: 'line_subsection',
            product_uom_qty: 0,
            price_unit: 0,
            price_total: 0,
        },
        { id: 9, name: "Sec3-sub1-r1", sequence: 9 },
        {
            id: 10,
            name: "Sec3-sub2",
            sequence: 10,
            display_type: 'line_subsection',
            product_uom_qty: 0,
            price_unit: 0,
            price_total: 0,
        },
        { id: 11, name: "Sec3-sub2-r1", sequence: 11 },
        {
            id: 12,
            name: "Sec4",
            sequence: 12,
            display_type: 'line_section',
            product_uom_qty: 0,
            price_unit: 0,
            price_total: 0,
            price_subtotal: 0
        },
        { id: 13, name: "Sec4-r1", sequence: 13 },
        {
            id: 14,
            name: "Sec4-sub1",
            sequence: 14,
            display_type: 'line_subsection',
            product_uom_qty: 0,
            price_unit: 0,
            price_total: 0,
            collapse_composition: true,
            collapse_prices: true,
        },
        { id: 15, name: "Sec4-sub1-r1", sequence: 15 },
    ];
}

class SaleOrder extends saleModels.SaleOrder {
    _records = [
        {
            id: 1,
            name: "Optional Sections Sale order",
            order_line: SaleOrderLine._records.map(record => record.id),
        },
    ];
    _views = {
        form: `
            <form>
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
                        <field name="name"/>
                        <field name="product_uom_qty"/>
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

defineModels({ SaleOrderLine, SaleOrder });
defineMailModels();

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

    expect(queryAllTexts('.o_data_row .o_list_text')).toEqual(EXPECTED_LINE_RECORDS);

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

    expect(queryAllTexts('.o_data_row .o_list_text')).toEqual(EXPECTED_LINE_RECORDS);

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

    expect(queryAllTexts('.o_data_row .o_list_text')).toEqual(EXPECTED_LINE_RECORDS);

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

    expect(queryAllTexts('.o_data_row .o_list_text')).toEqual(EXPECTED_LINE_RECORDS);

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

    expect(queryAllTexts('.o_data_row .o_list_text')).toEqual(EXPECTED_LINE_RECORDS);

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

    expect(queryAllTexts('.o_data_row .o_list_text')).toEqual(EXPECTED_LINE_RECORDS);

    await contains('.o_data_row:contains(Sec3):first .o_row_handle').dragAndDrop('.o_data_row:contains(Sec4):first');
    await clickSave();
    await expect.verifySteps(['web_save']);
})
