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

class SaleOrderTemplateLine extends models.ServerModel {
    _name = 'sale.order.template.line';

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
        },
        {
            id: 4,
            name: "Sec2",
            sequence: 4,
            display_type: 'line_section',
            product_uom_qty: 0,
        },
        {
            id: 5,
            name: "Sec3",
            sequence: 5,
            display_type: 'line_section',
            product_uom_qty: 0,
        },
        { id: 6, name: "Sec3-r1", sequence: 6 },
        { id: 7, name: "Sec3-r2", sequence: 7 },
        {
            id: 8,
            name: "Sec3-sub1",
            sequence: 8,
            display_type: 'line_subsection',
            product_uom_qty: 0,
        },
        { id: 9, name: "Sec3-sub1-r1", sequence: 9 },
        {
            id: 10,
            name: "Sec3-sub2",
            sequence: 10,
            display_type: 'line_subsection',
            product_uom_qty: 0,
        },
        { id: 11, name: "Sec3-sub2-r1", sequence: 11 },
        {
            id: 12,
            name: "Sec4",
            sequence: 12,
            display_type: 'line_section',
            product_uom_qty: 0,
        },
        { id: 13, name: "Sec4-r1", sequence: 13 },
        {
            id: 14,
            name: "Sec4-sub1",
            sequence: 14,
            display_type: 'line_subsection',
            product_uom_qty: 0,
        },
        { id: 15, name: "Sec4-sub1-r1", sequence: 15 },
    ];
}

class SaleOrderTemplate extends models.ServerModel {
    _name = 'sale.order.template';
    _records = [
        {
            id: 1,
            name: "Optional Sections Sale order template",
            sale_order_template_line_ids: SaleOrderTemplateLine._records.map(record => record.id),
        },
    ];
    _views = {
        form: `
            <form>
                <field
                    name="sale_order_template_line_ids"
                    widget="so_template_line_o2m"
                    options="{'subsections': True}"
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
                        <field name="display_type" column_invisible="1"/>
                        <field name="is_optional" column_invisible="1"/>
                    </list>
                </field>
            </form>
        `,
    };
}

defineModels({ SaleOrderTemplateLine, SaleOrderTemplate });
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

test("drag and drop regular template lines inside optional section resets some fields", async () => {
    SaleOrderTemplateLine._records.find(record => record.name === 'Sec3').is_optional = true;
    SaleOrderTemplateLine._records.find(record => record.name === 'Sec3-sub2-r1').product_uom_qty = 0;
    SaleOrderTemplateLine._records.find(record => record.name === 'Sec3-sub1-r1').product_uom_qty = 1;

    onRpc('web_save', ({ args }) => {
        expect.step('web_save');

        expect(
            args[1].sale_order_template_line_ids.find(
                commands => commands[1] === 13  // Sec4-r1
            )[2].product_uom_qty
        ).toEqual(0, {
            message: "Drag and drop inside optional section should reset product_uom_qty to 0"
        });
        expect(
            args[1].sale_order_template_line_ids.find(
                commands => commands[1] === 11  // Sec3-sub2-r1
            )[2].product_uom_qty
        ).toEqual(1, {
            message: "Drag and drop line with 0 quantity outside optional section should reset product_uom_qty to 1"
        });
        expect(
            args[1].sale_order_template_line_ids.find(
                commands => commands[1] === 9  // Sec3-sub1-r1
            )?.[2].product_uom_qty
        ).toEqual(undefined, {
            message: "Drag and drop line with non-zero quantity outside optional section shouldn't reset product_uom_qty"
        });
    })

    await mountView({
        type: 'form',
        resModel: 'sale.order.template',
        resId: 1,
    });

    expect(queryAllTexts('.o_data_row .o_list_text')).toEqual(EXPECTED_LINE_RECORDS);

    await contains('.o_data_row:contains(Sec4-r1):first .o_row_handle').dragAndDrop('.o_data_row:contains(Sec3-sub2):first');
    await contains('.o_data_row:contains(Sec3-sub2-r1):first .o_row_handle').dragAndDrop('.o_data_row:contains(Sec4-sub1):first');
    await contains('.o_data_row:contains(Sec3-sub1-r1):first .o_row_handle').dragAndDrop('.o_data_row:contains(Sec4-sub1):first');

    await clickSave();
    await expect.verifySteps(['web_save']);
})

test("Moving Optional Sections to include some template lines should set quantity to 0", async () => {
    SaleOrderTemplateLine._records.find(record => record.name === 'Sec4').is_optional = true;
    SaleOrderTemplateLine._records.find(record => record.name === 'Sec4-sub1-r1').product_uom_qty = 0;
    onRpc('web_save', ({ args }) => {
        expect.step('web_save');

        expect(
            args[1].sale_order_template_line_ids.find(
                commands => commands[1] === 7  // Sec3-r2
            )[2].product_uom_qty
        ).toEqual(0, {
            message: "New lines added to an optional section should have product_uom_qty set to 0",
        });
        expect(
            args[1].sale_order_template_line_ids.find(
                commands => commands[1] === 9  // Sec3-sub1-r1
            )[2].product_uom_qty
        ).toEqual(0, {
            message: "New lines added to a subsection of an optional section should also have product_uom_qty set to 0",
        });
        expect(
            args[1].sale_order_template_line_ids.find(
                commands => commands[1] === 13  // Sec4-r1
            )?.[2].product_uom_qty
        ).toEqual(undefined, {
            message: "Existing optional lines should keep their current product_uom_qty",
        });
    });

    await mountView({
        type: 'form',
        resModel: 'sale.order.template',
        resId: 1,
    });

    expect(queryAllTexts('.o_data_row .o_list_text')).toEqual(EXPECTED_LINE_RECORDS);

    await contains('.o_data_row:contains(Sec4):first .o_row_handle').dragAndDrop('.o_data_row:contains(Sec3-r2):first');
    await clickSave();
    await expect.verifySteps(['web_save']);
})

test("Moving Optional Sections to exclude some template lines should set quantity to 1", async () => {
    SaleOrderTemplateLine._records.find(record => record.name === 'Sec3').is_optional = true;
    SaleOrderTemplateLine._records.find(record => record.name === 'Sec3-r1').product_uom_qty = 0;
    SaleOrderTemplateLine._records.find(record => record.name === 'Sec3-sub1-r1').product_uom_qty = 0;
    onRpc('web_save', ({ args }) => {
        expect.step('web_save');

        expect(
            args[1].sale_order_template_line_ids.find(
                command => command[1] === 6  // Sec3-r1
            )[2].product_uom_qty
        ).toEqual(1, {
            message: "Non-optional lines should reset product_uom_qty to 1 when it was previously 0.",
        });
        expect(
            args[1].sale_order_template_line_ids.find(
                command => command[1] === 7  // Sec3-r2
            )?.[2].product_uom_qty
        ).toEqual(undefined, {
            message: "Non-optional lines should keep their existing product_uom_qty when it was already non-zero.",
        });
        expect(
            args[1].sale_order_template_line_ids.find(
                command => command[1] === 9  // Sec3-sub1-r1
            )[2].product_uom_qty
        ).toEqual(1, {
            message: "Lines moved out of an optional subsection should reset product_uom_qty to 1 when it was 0.",
        });
        expect(
            args[1].sale_order_template_line_ids.find(
                command => command[1] === 11  // Sec3-sub2-r1
            )?.[2].product_uom_qty
        ).toEqual(undefined, {
            message: "Lines moved out of an optional subsection should keep their existing product_uom_qty when it was already non-zero.",
        });
    });

    await mountView({
        type: 'form',
        resModel: 'sale.order.template',
        resId: 1,
    });

    expect(queryAllTexts('.o_data_row .o_list_text')).toEqual(EXPECTED_LINE_RECORDS);

    await contains('.o_data_row:contains(Sec3):first .o_row_handle').dragAndDrop('.o_data_row:contains(Sec4):first');
    await clickSave();
    await expect.verifySteps(['web_save']);
})
