import { defineMailModels } from '@mail/../tests/mail_test_helpers';
import { expect, test } from '@odoo/hoot';
import { queryAllTexts } from '@odoo/hoot-dom';
import {
    clickSave,
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from '@web/../tests/web_test_helpers';

class SaleOrderLine extends models.Model {
    _name = 'sale.order.line';
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

    name = fields.Char();
    sequence = fields.Integer();
    product_uom_qty = fields.Integer({ default: 2 });
    price_unit = fields.Float({ default: 10 });
    price_total = fields.Float({ default: 22 });
    price_subtotal = fields.Float({ default: 20 });
    display_type = fields.Selection({
        default: false,
        selection: [
        ['line_section', "Section"],
        ['line_subsection', "Subsection"],
        ['line_note', "Note"],
        ],
    });
    collapse_prices = fields.Boolean();
    collapse_composition = fields.Boolean();
    is_optional = fields.Boolean();
}

class SaleOrder extends models.Model {
    _name = 'sale.order'
    _records = [
        {
            id: 1,
            name: "Optional Sections Sale order",
            order_line: SaleOrderLine._records.map(record => record.id),
        },
    ]

    name = fields.Char()
    order_line = fields.One2many({ relation: 'sale.order.line' })
}

defineModels([SaleOrderLine, SaleOrder]);
defineMailModels();

test("Can't mark section hidden if optional and vice versa also setting optional resets some fields", async () => {
    let rpcCounter = 0;
    // Need feedback on this not sure how else we can test another web_save here
    onRpc('web_save', ({ args }) => {
        rpcCounter++;
        if (rpcCounter === 1) {
            expect.step('web_save');
            expect(args[1]).toEqual(
                {
                    order_line: [
                        [1, 5, { is_optional: true }],
                        [1, 6, { product_uom_qty: 0, price_total: 0, price_subtotal: 0 }],
                        [1, 7, { product_uom_qty: 0, price_total: 0, price_subtotal: 0 }],
                        [1, 8, { collapse_composition: false, collapse_prices: false }],
                        [1, 9, { product_uom_qty: 0, price_total: 0, price_subtotal: 0 }],
                        [1, 10, { collapse_composition: false, collapse_prices: false }],
                        [1, 11, { product_uom_qty: 0, price_total: 0, price_subtotal: 0 }],
                    ],
                },
                { message:"The subsections should reset collaspe_ fields' value and product lines should be set with 0 quantity and price as soon as section is set to optional" }
            );
        } else if (rpcCounter === 2) {
            expect.step('web_save');
            expect(args[1]).toEqual(
                {
                    order_line: [
                        [1, 5, { is_optional: false }],
                        [1, 6, { product_uom_qty: 1 }],
                        [1, 7, { product_uom_qty: 1 }],
                        [1, 9, { product_uom_qty: 1 }],
                        [1, 11, { product_uom_qty: 1 }],
                    ],
                },
                { message:"The subsections should reset products lines with 0 quantity with 1 soon as section is set to optional" }
            );
        }
    });

    await mountView({
        type: 'form',
        resModel: 'sale.order',
        resId: 1,
        arch: `
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
    });

    expect(queryAllTexts('.o_data_row .o_list_char')).toEqual([
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
    ]);

    await contains('.o_data_row:contains(Sec1) .o_list_section_options button').click();
    expect('.o-dropdown-item:contains(Set Optional)').toHaveClass('disabled', {
        message: "Section with hidden prices can't be optional"
    });

    await contains('.o_data_row:contains(Sec2) .o_list_section_options button').click();
    expect('.o-dropdown-item:contains(Set Optional)').toHaveClass('disabled', {
        message: "Hidden section can't be optional"
    });

    await contains('.o_data_row:contains(Sec3) .o_list_section_options button').click();
    await contains('.o-dropdown-item:contains(Set Optional)').click();

    await clickSave();
    await expect.verifySteps(['web_save']);
    
    expect('.o_data_row:contains(Sec3)').toHaveClass('text-primary', {
        message: "Optional section should be text-primary"
    });
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

test("drag and drop inside optional section resets some fields", async () => {
    SaleOrderLine._records.find(record => record.name === 'Sec3').is_optional = true;
    SaleOrderLine._records.find(record => record.name === 'Sec3-sub2-r1').product_uom_qty = 0;

    onRpc('web_save', ({ args }) => {
        expect.step('web_save');
        expect(args[1].order_line.find(commands => commands[1] === 13)[2].product_uom_qty).toEqual(0, {
            message: "Drag and drop inside optional section should reset product_uom_qty to 0"
        });
        expect(args[1].order_line.find(commands => commands[1] === 11)[2].product_uom_qty).toEqual(1, {
            message: "Drag and drop line with 0 quantity outside optional section should reset product_uom_qty to 1"
        });
        expect(args[1].order_line.find(commands => commands[1] === 9)[2].product_uom_qty).toEqual(undefined, {
            message: "Drag and drop line with non-zero quantity outside optional section shouldn't reset product_uom_qty"
        });
    })

    await mountView({
        type: 'form',
        resModel: 'sale.order',
        resId: 1,
        arch: `
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
    });

    expect(queryAllTexts('.o_data_row .o_list_char')).toEqual([
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
    ]);

    await contains('.o_data_row:contains(Sec4-r1):first .o_row_handle').dragAndDrop('.o_data_row:contains(Sec3-sub2):first');
    await contains('.o_data_row:contains(Sec3-sub2-r1):first .o_row_handle').dragAndDrop('.o_data_row:contains(Sec4-sub1):first');
    await contains('.o_data_row:contains(Sec3-sub1-r1):first .o_row_handle').dragAndDrop('.o_data_row:contains(Sec4-sub1):first');

    await clickSave();
    await expect.verifySteps(['web_save']);
})
