import { defineMailModels } from '@mail/../tests/mail_test_helpers';
import { expect, test } from '@odoo/hoot';
import { queryAllTexts } from '@odoo/hoot-dom';
import {
    clickCancel,
    contains,
    defineModels,
    fields,
    mountView,
} from '@web/../tests/web_test_helpers';
import { defineComboModels } from '@product/../tests/product_combo_test_helpers';
import { saleModels } from './sale_test_helpers';

class SaleOrderLine extends saleModels.SaleOrderLine {
    _records = [
        { id: 1, name: "Non Combo Line1", product_id: 1, sequence: 1 },
        { id: 2, name: "Non Combo Line2", product_id: 2, sequence: 2 },
        { id: 3, name: "Test Combo1", product_id: 5, sequence: 3, product_type: 'combo' },
        { id: 4, name: "Combo1 Item 1", product_id: 3, combo_item_id: 3, linked_line_id: 3, sequence: 4 },
        { id: 5, name: "Combo1 Item 2", product_id: 1, combo_item_id: 1, linked_line_id: 3, sequence: 5 },
        { id: 6, name: "Test Combo2", product_id: 5, sequence: 6, product_type: 'combo' },
        { id: 7, name: "Combo2 Item 1", product_id: 4, combo_item_id: 4, linked_line_id: 6, sequence: 7 },
        { id: 8, name: "Combo2 Item 2", product_id: 2, combo_item_id: 2, linked_line_id: 6, sequence: 8 },
        { id: 9, name: "Non Combo Line3", product_id: 1, sequence: 9 },
    ];
}

class SaleOrder extends saleModels.SaleOrder {
    _records = [
        {
            id: 1,
            name: "Combo Sale order",
            order_line: SaleOrderLine._records.map(record => record.id),
        },
    ]
}

defineComboModels();
defineModels({ SaleOrderLine, SaleOrder });
defineMailModels();

test("test combo move up/down", async () => {
    await mountView({
        type: 'form',
        resModel: 'sale.order',
        resId: 1,
        arch: `
            <form>
                <field
                    name="order_line"
                    widget="sol_o2m"
                    options="{'subsections': True}"
                >
                    <list editable="bottom">
                        <control>
                            <create name="add_line_control" string="Add a line"/>
                            <create name="add_section_control" string="Add a section" context="{'default_display_type': 'line_section'}"/>
                            <create name="add_note_control" string="Add a note" context="{'default_display_type': 'line_note'}"/>
                        </control>
                        <field name="sequence" widget="handle" invisible="combo_item_id"/>
                        <field name="name"/>
                        <field name="display_type" column_invisible="1"/>
                        <field name="linked_line_id" column_invisible="1"/>
                        <field name="product_type" column_invisible="1"/>
                        <field name="combo_item_id" column_invisible="1"/>
                    </list>
                </field>
            </form>
        `,
    });

    expect(queryAllTexts('.o_data_row')).toEqual([
        "Non Combo Line1",
        "Non Combo Line2",
        "Test Combo1",
            "Combo1 Item 1",
            "Combo1 Item 2",
        "Test Combo2",
            "Combo2 Item 1",
            "Combo2 Item 2",
        "Non Combo Line3",
    ]);

    await contains('.o_data_row:contains(Test Combo1) .o_list_section_options button').click();
    expect('.o-dropdown-item:contains(Move Up)').toHaveCount(1, {
        message: 'Move up option should be there for Test combo1 line having SO lines before and after'
    });
    expect('.o-dropdown-item:contains(Move Down)').toHaveCount(1, {
        message: 'Move down option should be there for Test combo1 line having SO lines before and after'
    });

    await contains('.o-dropdown-item:contains(Move Up)').click();
    await contains('.o_data_row:contains(Test Combo1) .o_list_section_options button').click();
    await contains('.o-dropdown-item:contains(Move Up)').click();

    await contains('.o_data_row:contains(Test Combo1) .o_list_section_options button').click();
    expect('.o-dropdown-item:contains(Move Up)').toHaveCount(0, {
        message: 'Move up option should be invisible for Test combo1 since there aren\'t any non combo SO lines before'
    });

    await contains('.o_data_row:contains(Test Combo2) .o_list_section_options button').click();
    expect('.o-dropdown-item:contains(Move Up)').toHaveCount(1, {
        message: 'Move up option should be there for Test combo2 line having SO lines before and after'
    });
    expect('.o-dropdown-item:contains(Move Down)').toHaveCount(1, {
        message: 'Move down option should be there for Test combo2 line having SO lines before and after'
    });

    await contains('.o-dropdown-item:contains(Move Down)').click();

    await contains('.o_data_row:contains(Test Combo2) .o_list_section_options button').click();
    expect('.o-dropdown-item:contains(Move Down)').toHaveCount(0, {
        message: 'Move down option should be invisible for Test combo2 since there aren\'t any non combo SO lines after'
    });

    expect(queryAllTexts('.o_data_row')).toEqual([
        "Test Combo1",
            "Combo1 Item 1",
            "Combo1 Item 2",
        "Non Combo Line1",
        "Non Combo Line2",
        "Non Combo Line3",
        "Test Combo2",
            "Combo2 Item 1",
            "Combo2 Item 2",
    ], {
        message: 'Test combo1 line should be moved up two lines and Test combo2 line should be moved down one line'
    });

    await clickCancel();

    expect(queryAllTexts('.o_data_row')).toEqual([
        "Non Combo Line1",
        "Non Combo Line2",
        "Test Combo1",
            "Combo1 Item 1",
            "Combo1 Item 2",
        "Test Combo2",
            "Combo2 Item 1",
            "Combo2 Item 2",
        "Non Combo Line3",
    ]);

    await contains('.o_data_row:contains(Test Combo1) .o_list_section_options button').click();
    await contains('.o-dropdown-item:contains(Move Down)').click();

    expect(queryAllTexts('.o_data_row')).toEqual([
        "Non Combo Line1",
        "Non Combo Line2",
        "Test Combo2",
            "Combo2 Item 1",
            "Combo2 Item 2",
        "Test Combo1",
            "Combo1 Item 1",
            "Combo1 Item 2",
        "Non Combo Line3",
    ], {
        message: 'Test combo1 and Test combo2 should be swapped when moving Test combo1 down'
    });

    await clickCancel();

    await contains('.o_data_row:contains(Test Combo2) .o_list_section_options button').click();
    await contains('.o-dropdown-item:contains(Move Up)').click();

    expect(queryAllTexts('.o_data_row')).toEqual([
        "Non Combo Line1",
        "Non Combo Line2",
        "Test Combo2",
            "Combo2 Item 1",
            "Combo2 Item 2",
        "Test Combo1",
            "Combo1 Item 1",
            "Combo1 Item 2",
        "Non Combo Line3",
    ], {
        message: 'Test combo1 and Test combo2 should be swapped when moving Test combo2 up'
    });
})

test("Test combo columns", async () => {
    // Set different defaults for checking aggregation of columns on combo line
    SaleOrderLine._fields.price_unit = fields.Float({ default: 3.00 });
    SaleOrderLine._fields.price_total = fields.Float({ default: 3.00 });
    SaleOrderLine._fields.product_uom_qty = fields.Float({ default: 3.00 });
    SaleOrderLine._fields.discount = fields.Integer({ default: 30 });
    await mountView({
        type: 'form',
        resModel: 'sale.order',
        resId: 1,
        arch: `
            <form>
                <field
                    name="order_line"
                    widget="sol_o2m"
                    options="{'subsections': True}"
                    aggregated_fields="price_total"
                >
                    <list editable="bottom">
                        <control>
                            <create name="add_line_control" string="Add a line"/>
                            <create name="add_section_control" string="Add a section" context="{'default_display_type': 'line_section'}"/>
                            <create name="add_note_control" string="Add a note" context="{'default_display_type': 'line_note'}"/>
                        </control>
                        <field name="sequence" widget="handle" invisible="combo_item_id"/>
                        <field name="name"/>
                        <field name="price_unit"/>
                        <field name="product_uom_qty"/>
                        <field name="discount"/>
                        <field name="price_total"/>
                        <field name="display_type" column_invisible="1"/>
                        <field name="linked_line_id" column_invisible="1"/>
                        <field name="product_type" column_invisible="1"/>
                        <field name="combo_item_id" column_invisible="1"/>
                    </list>
                </field>
            </form>
        `,
    });

    expect(queryAllTexts('.o_data_row .o_list_text')).toEqual([
        "Non Combo Line1",
        "Non Combo Line2",
        "Test Combo1",
            "Combo1 Item 1",
            "Combo1 Item 2",
        "Test Combo2",
            "Combo2 Item 1",
            "Combo2 Item 2",
        "Non Combo Line3",
    ]);

    expect(queryAllTexts('.o_data_row:contains(Test Combo1) > td').filter(Boolean)).toEqual([
        "Test Combo1", // name
        "3.00", // product_uom_qty
        "30",  // discount
        "9.00",  // price_total
    ], {
        message: 'combo line should only have name, product_uom_qty, discount and `aggregated_fields` columns'
    });

    expect(queryAllTexts('.o_data_row:contains(Non Combo Line1) > td').filter(Boolean)).toEqual([
        "Non Combo Line1", // name
        "3.00",  // price_unit
        "3.00",  // product_uom_qty
        "30",  // discount
        "3.00",  // price_total
    ], {
        message: 'Non-combo line should have all columns'
    });
})
