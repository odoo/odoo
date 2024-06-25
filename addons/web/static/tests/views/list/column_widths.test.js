import { describe, expect, getFixture, test } from "@odoo/hoot";
import { queryAll, queryAllProperties, queryFirst, queryRect, resize } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    pagerNext,
    serverState,
    webModels,
} from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

const { ResCompany, ResPartner, ResUsers } = webModels;

class Foo extends models.Model {
    foo = fields.Char();
    bar = fields.Boolean();
    date = fields.Date();
    datetime = fields.Datetime();
    int_field = fields.Integer();
    qux = fields.Float();
    m2o = fields.Many2one({ relation: "bar" });
    o2m = fields.One2many({ relation: "bar" });
    m2m = fields.Many2many({ relation: "bar" });
    text = fields.Text();
    amount = fields.Monetary({ currency_field: "currency_id" });
    currency_id = fields.Many2one({ relation: "res.currency", default: 1 });
    reference = fields.Reference({
        selection: [
            ["bar", "Bar"],
            ["res.currency", "Currency"],
        ],
    });

    _records = [
        {
            id: 1,
            foo: "yop",
            bar: true,
            date: "2017-01-25",
            datetime: "2016-12-12 10:55:05",
            int_field: 10,
            qux: 0.4,
            m2o: 1,
            m2m: [1, 2],
            amount: 1200,
            currency_id: 2,
            reference: "bar,1",
        },
        {
            id: 2,
            foo: "blip",
            bar: true,
            int_field: 9,
            qux: 13,
            m2o: 2,
            m2m: [1, 2, 3],
            amount: 500,
            reference: "res.currency,1",
        },
        {
            id: 3,
            foo: "gnap",
            bar: true,
            int_field: 17,
            qux: -3,
            m2o: 1,
            m2m: [],
            amount: 300,
            reference: "res.currency,2",
        },
        {
            id: 4,
            foo: "blip",
            bar: false,
            int_field: -4,
            qux: 9,
            m2o: 1,
            m2m: [1],
            amount: 0,
        },
    ];
}

class Bar extends models.Model {
    name = fields.Char();

    _records = [
        { id: 1, name: "Value 1" },
        { id: 2, name: "Value 2" },
        { id: 3, name: "Value 3" },
    ];
}

class Currency extends models.Model {
    _name = "res.currency";

    name = fields.Char();
    symbol = fields.Char();
    position = fields.Selection({
        selection: [
            ["after", "A"],
            ["before", "B"],
        ],
    });

    _records = [
        { id: 1, name: "USD", symbol: "$", position: "before" },
        { id: 2, name: "EUR", symbol: "€", position: "after" },
    ];
}

defineModels([Foo, Bar, Currency, ResCompany, ResPartner, ResUsers]);

test(`editable rendering with handle and no data`, async () => {
    Foo._records = [];

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <tree editable="bottom">
                <field name="int_field" widget="handle"/>
                <field name="currency_id"/>
                <field name="m2o"/>
            </tree>
        `,
    });
    expect(`thead th`).toHaveCount(4, { message: "there should be 4 th" });
    expect(`thead th:eq(0)`).toHaveClass("o_list_record_selector");
    expect(`thead th:eq(1)`).toHaveClass("o_handle_cell");
    expect(`thead th:eq(0)`).toHaveText("", {
        message: "the handle field shouldn't have a header description",
    });
    expect(`thead th:eq(2)`).toHaveAttribute("style", "width: 50%;");
    expect(`thead th:eq(3)`).toHaveAttribute("style", "width: 50%;");
});

test(`column widths should depend on the content when there is data`, async () => {
    Foo._records[0].foo = "Some very very long value for a char field";

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <tree editable="top">
                <field name="bar"/>
                <field name="foo"/>
                <field name="int_field"/>
                <field name="qux"/>
                <field name="date"/>
                <field name="datetime"/>
            </tree>
        `,
        limit: 2,
    });
    expect(Math.floor(queryRect(`thead .o_list_record_selector:eq(0)`).width)).toBe(41);
    const widthPage1 = Math.floor(queryRect(`th[data-name=foo]`).width);

    await pagerNext();
    expect(Math.floor(queryRect(`thead .o_list_record_selector:eq(0)`).width)).toBe(41);
    const widthPage2 = Math.floor(queryRect(`th[data-name=foo]`).width);
    expect(widthPage1).toBeGreaterThan(widthPage2, {
        message: "column widths should be computed dynamically according to the content",
    });
});

test(`width of some of the fields should be hardcoded if no data`, async () => {
    Foo._records = [];

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <tree editable="top">
                <field name="bar"/>
                <field name="foo"/>
                <field name="int_field"/>
                <field name="qux"/>
                <field name="date"/>
                <field name="datetime"/>
                <field name="amount"/>
                <field name="currency_id" width="25px"/>
            </tree>
        `,
    });
    expect(`.o_resize`).toHaveCount(8);
    expect(Math.floor(queryRect(`th[data-name="bar"]`).width)).toBe(70);
    expect(Math.floor(queryRect(`th[data-name="int_field"]`).width)).toBe(74);
    expect(Math.floor(queryRect(`th[data-name="qux"]`).width)).toBe(92);
    expect(Math.floor(queryRect(`th[data-name="date"]`).width)).toBe(92);
    expect(Math.floor(queryRect(`th[data-name="datetime"]`).width)).toBe(146);
    expect(Math.floor(queryRect(`th[data-name="amount"]`).width)).toBe(104);
    expect(`th[data-name="foo"]`).toHaveAttribute("style", /width: 100%/);
    expect(Math.floor(queryRect(`th[data-name="currency_id"]`).width)).toBe(25);
});

test(`width of some fields should be hardcoded if no data, and list initially invisible`, async () => {
    Foo._fields.foo_o2m = fields.One2many({ relation: "foo" });

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <notebook>
                        <page string="Page1"></page>
                        <page string="Page2">
                            <field name="foo_o2m">
                                <tree editable="bottom">
                                    <field name="bar"/>
                                    <field name="foo"/>
                                    <field name="int_field"/>
                                    <field name="qux"/>
                                    <field name="date"/>
                                    <field name="datetime"/>
                                    <field name="amount"/>
                                    <field name="currency_id" width="25px"/>
                                </tree>
                            </field>
                        </page>
                    </notebook>
                </sheet>
            </form>
        `,
        resId: 1,
        mode: "edit",
    });
    expect(`.o_field_one2many`).toHaveCount(0);

    await contains(`.nav-item:eq(-1) .nav-link`).click();
    expect(`.o_field_one2many .o_resize`).toHaveCount(8);
    expect(Math.floor(queryRect(`.o_field_one2many th[data-name="bar"]`).width)).toBe(70);
    expect(Math.floor(queryRect(`.o_field_one2many th[data-name="int_field"]`).width)).toBe(74);
    expect(Math.floor(queryRect(`.o_field_one2many th[data-name="qux"]`).width)).toBe(92);
    expect(Math.floor(queryRect(`.o_field_one2many th[data-name="date"]`).width)).toBe(92);
    expect(Math.floor(queryRect(`.o_field_one2many th[data-name="datetime"]`).width)).toBe(146);
    expect(Math.floor(queryRect(`.o_field_one2many th[data-name="amount"]`).width)).toBe(104);
    expect(`.o_field_one2many th[data-name="foo"]`).toHaveAttribute("style", /width: 100%/);
    expect(Math.floor(queryRect(`.o_field_one2many th[data-name="currency_id"]`).width)).toBe(25);
    expect(Math.floor(queryRect(`.o_list_actions_header`).width)).toBe(32);
});

test(`empty editable list with the handle widget and no content help`, async () => {
    // no records for the foo model
    Foo._records = [];

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <tree editable="bottom">
                <field name="int_field" widget="handle"/>
                <field name="foo"/>
            </tree>
        `,
        noContentHelp: '<p class="hello">click to add a foo</p>',
    });
    expect(`.o_view_nocontent`).toHaveCount(1, { message: "should have no content help" });

    // click on create button
    await contains(`.o_list_button_add`).click();
    expect(`thead > tr > th.o_handle_cell`).toHaveStyle(
        { width: "33px" },
        {
            message: "While creating first record, width should be applied to handle widget.",
        }
    );

    // creating one record
    await contains(`.o_selected_row [name='foo'] input`).edit("test_foo", { confirm: false });
    await contains(`.o_list_button_save`).click();
    expect(`thead > tr > th.o_handle_cell`).toHaveStyle(
        { width: "33px" },
        {
            message:
                "After creation of the first record, width of the handle widget should remain as it is",
        }
    );
});

test(`editable list: overflowing table`, async () => {
    class Abc extends models.Model {
        titi = fields.Char();
        grosminet = fields.Char();

        _records = [
            {
                id: 1,
                titi: "Tiny text",
                grosminet:
                    // Just want to make sure that the table is overflowed
                    `Lorem ipsum dolor sit amet, consectetur adipiscing elit.
                    Donec est massa, gravida eget dapibus ac, eleifend eget libero.
                    Suspendisse feugiat sed massa eleifend vestibulum. Sed tincidunt
                    velit sed lacinia lacinia. Nunc in fermentum nunc. Vestibulum ante
                    ipsum primis in faucibus orci luctus et ultrices posuere cubilia
                    Curae; Nullam ut nisi a est ornare molestie non vulputate orci.
                    Nunc pharetra porta semper. Mauris dictum eu nulla a pulvinar. Duis
                    eleifend odio id ligula congue sollicitudin. Curabitur quis aliquet
                    nunc, ut aliquet enim. Suspendisse malesuada felis non metus
                    efficitur aliquet.`,
            },
        ];
    }
    defineModels([Abc]);

    await mountView({
        resModel: "abc",
        type: "list",
        arch: `
            <tree editable="top">
                <field name="titi"/>
                <field name="grosminet" widget="char"/>
            </tree>
        `,
    });
    expect(`table`).toHaveRect(queryRect`.o_list_renderer`, {
        message: "Table should not be stretched by its content",
    });
});

test(`editable list: overflowing table (3 columns)`, async () => {
    const longText = `Lorem ipsum dolor sit amet, consectetur adipiscing elit.
                    Donec est massa, gravida eget dapibus ac, eleifend eget libero.
                    Suspendisse feugiat sed massa eleifend vestibulum. Sed tincidunt
                    velit sed lacinia lacinia. Nunc in fermentum nunc. Vestibulum ante
                    ipsum primis in faucibus orci luctus et ultrices posuere cubilia
                    Curae; Nullam ut nisi a est ornare molestie non vulputate orci.
                    Nunc pharetra porta semper. Mauris dictum eu nulla a pulvinar. Duis
                    eleifend odio id ligula congue sollicitudin. Curabitur quis aliquet
                    nunc, ut aliquet enim. Suspendisse malesuada felis non metus
                    efficitur aliquet.`;

    class Abc extends models.Model {
        titi = fields.Char();
        grosminet1 = fields.Char();
        grosminet2 = fields.Char();
        grosminet3 = fields.Char();

        _records = [
            {
                id: 1,
                titi: "Tiny text",
                grosminet1: longText,
                grosminet2: longText + longText,
                grosminet3: longText + longText + longText,
            },
        ];
    }
    defineModels([Abc]);

    await mountView({
        resModel: "abc",
        type: "list",
        arch: `
            <tree editable="top">
                <field name="titi"/>
                <field name="grosminet1" class="large"/>
                <field name="grosminet3" class="large"/>
                <field name="grosminet2" class="large"/>
            </tree>
        `,
    });
    expect(`table`).toHaveRect(queryRect`.o_list_renderer`);

    const largeCells = queryAll(`.o_data_cell.large`);
    expect(Math.abs(largeCells[0].offsetWidth - largeCells[1].offsetWidth) <= 1).toBe(true);
    expect(Math.abs(largeCells[1].offsetWidth - largeCells[2].offsetWidth) <= 1).toBe(true);
    expect(queryFirst(`.o_data_cell:not(.large)`).offsetWidth < largeCells[0].offsetWidth).toBe(
        true
    );
});

test(`empty list: state with nameless and stringless buttons`, async () => {
    Foo._records = [];

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <tree>
                <field name="foo"/>
                <button string="choucroute"/>
                <button icon="fa-heart"/>
            </tree>
        `,
    });
    expect(`th:contains(Foo)`).toHaveAttribute("style", /width: 50%/);
    expect(`th:eq(-1)`).toHaveAttribute("style", /width: 50%/);
});

test(`list: column: resize, reorder, resize again`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <tree>
                <field name="foo"/>
                <field name="int_field"/>
            </tree>
        `,
    });

    // 1. Resize column foo to middle of column int_field.
    const originalWidths = queryAllProperties(`.o_list_table th`, "offsetWidth");
    await contains(`th:eq(1) .o_resize`, { visible: false }).dragAndDrop(`th:eq(2)`);
    let widthsAfterResize = queryAllProperties(`.o_list_table th`, "offsetWidth");
    expect(widthsAfterResize[0]).toBe(originalWidths[0]);
    expect(widthsAfterResize[1]).toBeGreaterThan(originalWidths[1]);

    // 2. Reorder column foo.
    await contains(`th:eq(1)`).click();
    const widthsAfterReorder = queryAllProperties(`.o_list_table th`, "offsetWidth");
    expect(widthsAfterResize[0]).toBe(widthsAfterReorder[0]);
    expect(widthsAfterResize[1]).toBe(widthsAfterReorder[1]);

    // 3. Resize again, this time check sizes while dragging and after drop.
    const { moveTo, drop } = await contains(`th:eq(1) .o_resize`, { visible: false }).drag();
    await moveTo(`th:eq(2)`);
    widthsAfterResize = queryAllProperties(`.o_list_table th`, "offsetWidth");
    expect(widthsAfterResize[1]).toBeGreaterThan(widthsAfterReorder[1]);

    await drop();
    expect(widthsAfterResize[1]).toBeGreaterThan(widthsAfterReorder[1]);
});

test(`list: resize column and toggle one checkbox`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <tree>
                <field name="foo"/>
                <field name="int_field"/>
            </tree>
        `,
    });

    // 1. Resize column foo to middle of column int_field.
    await contains(`th:eq(1) .o_resize`, { visible: false }).dragAndDrop(`th:eq(2)`);
    const widthsAfterResize = queryAllProperties(`.o_list_table th`, "offsetWidth");

    // 2. Column size should be the same after selecting a row
    await contains(`tbody .o_list_record_selector`).click();
    const widthsAfterSelectRow = queryAllProperties(`.o_list_table th`, "offsetWidth");
    expect(widthsAfterResize[0]).toBe(widthsAfterSelectRow[0], {
        message: "Width must not have been changed after selecting a row",
    });
    expect(widthsAfterResize[1]).toBe(widthsAfterSelectRow[1], {
        message: "Width must not have been changed after selecting a row",
    });
});

test(`list: resize column and toggle check all`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <tree>
                <field name="foo"/>
                <field name="int_field"/>
            </tree>
        `,
    });

    // 1. Resize column foo to middle of column int_field.
    await contains(`th:eq(1) .o_resize`, { visible: false }).dragAndDrop(`th:eq(2)`);
    const widthsAfterResize = queryAllProperties(`.o_list_table th`, "offsetWidth");

    // 2. Column size should be the same after selecting all
    await contains(`thead .o_list_record_selector`).click();
    const widthsAfterSelectAll = queryAllProperties(`.o_list_table th`, "offsetWidth");
    expect(widthsAfterResize[0]).toBe(widthsAfterSelectAll[0], {
        message: "Width must not have been changed after selecting all",
    });
    expect(widthsAfterResize[1]).toBe(widthsAfterSelectAll[1], {
        message: "Width must not have been changed after selecting all",
    });
});

test(`editable list: resize column headers`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <tree editable="top">
                <field name="foo"/>
                <field name="reference" optional="hide"/>
            </tree>
        `,
    });
    const originalWidths = queryAllProperties(`.o_list_table th`, "offsetWidth");
    await contains(`th:eq(1) .o_resize`, { visible: false }).dragAndDrop(`th:eq(2)`);

    const finalWidths = queryAllProperties(`.o_list_table th`, "offsetWidth");
    expect(finalWidths[0]).toBe(originalWidths[0]);
    expect(finalWidths[2]).toBe(originalWidths[2]);
});

test.todo(`editable list: resize column headers (2)`, async () => {
    // This test will ensure that, on resize list header,
    // the resized element have the correct size and other elements are not resized
    Foo._records[0].foo = "a".repeat(200);

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <tree editable="top">
                <field name="foo"/>
                <field name="bar"/>
                <field name="reference" optional="hide"/>
            </tree>
        `,
    });
    const originalWidth1 = queryRect(`th:eq(1)`).width;
    const originalWidth2 = queryRect(`th:eq(2)`).width;

    await contains(`th:eq(1) .o_resize`, { visible: false }).dragAndDrop(`th:eq(2) .o_resize`, {
        visible: false,
    });
    const finalWidth1 = queryRect(`th:eq(1)`).width;
    const finalWidth2 = queryRect(`th:eq(2)`).width;
    expect(
        Math.abs(Math.floor(finalWidth1) - Math.floor(originalWidth1 + originalWidth2))
    ).toBeLessThan(1);
    expect(Math.floor(finalWidth2)).toBe(Math.floor(originalWidth2));
});

test(`resize column with several x2many lists in form group`, async () => {
    Bar._fields.text = fields.Char();
    Foo._records[0].o2m = [1, 2];

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form>
                <group>
                    <field name="o2m">
                        <tree editable="bottom">
                            <field name="display_name"/>
                            <field name="text"/>
                        </tree>
                    </field>
                    <field name="m2m">
                        <tree editable="bottom">
                            <field name="display_name"/>
                            <field name="text"/>
                        </tree>
                    </field>
                </group>
            </form>
        `,
        resId: 1,
    });
    const initialWidth0 = queryRect(`.o_field_x2many_list table:eq(0)`).width;
    const initialWidth1 = queryRect(`.o_field_x2many_list table:eq(1)`).width;
    expect(initialWidth0).toBe(initialWidth1, {
        message: "both table columns have same width",
    });

    await contains(`th:eq(0) .o_resize`, { visible: false }).dragAndDrop(`th:eq(1)`, {
        position: "right",
    });
    expect(`.o_field_x2many_list table:eq(0)`).not.toHaveRect(
        { width: initialWidth0 },
        {
            message: "first o2m table is resized and width of table has changed",
        }
    );
    expect(`.o_field_x2many_list table:eq(1)`).toHaveRect(
        { width: initialWidth1 },
        {
            message: "second o2m table should not be impacted on first o2m in group resized",
        }
    );
});

test(`resize column with x2many list with several fields in form notebook`, async () => {
    Foo._records[0].o2m = [1, 2];

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <notebook>
                        <page string="Page 1">
                            <field name="o2m">
                                <tree editable="bottom">
                                    <field name="display_name"/>
                                    <field name="display_name"/>
                                    <field name="display_name"/>
                                    <field name="display_name"/>
                                </tree>
                            </field>
                        </page>
                    </notebook>
                </sheet>
            </form>
        `,
        resId: 1,
    });

    const listInitialWidth = queryRect(`.o_list_renderer`).width;
    await contains(`th:eq(0) .o_resize`, { visible: false }).dragAndDrop(`th:eq(1)`, {
        position: "right",
    });
    expect(`.o_list_renderer`).toHaveRect(
        { width: listInitialWidth },
        {
            message: "resizing the column should not impact the width of list",
        }
    );
});

test(`editable list: unnamed columns cannot be resized`, async () => {
    Foo._records = [{ id: 1, o2m: [1] }];
    Bar._records = [{ id: 1, display_name: "Oui" }];

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="o2m">
                        <tree editable="top">
                            <field name="display_name"/>
                            <button name="the_button" icon="fa-heart"/>
                        </tree>
                    </field>
                </sheet>
            </form>
        `,
        resId: 1,
        mode: "edit",
    });
    expect(queryRect(`.o_field_one2many th:eq(0)`).right).toBe(
        queryRect(`.o_field_one2many th:eq(0) .o_resize`).right,
        {
            message: "First resize handle should be attached at the end of the first header",
        }
    );
    expect(`.o_field_one2many th:eq(1) .o_resize`).toHaveCount(0, {
        message: "Columns without name should not have a resize handle",
    });
});

test(`width of some of the fields should be hardcoded if no data (grouped case)`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <tree editable="top">
                <field name="bar"/>
                <field name="foo"/>
                <field name="int_field"/>
                <field name="qux"/>
                <field name="date"/>
                <field name="datetime"/>
                <field name="amount"/>
                <field name="currency_id" width="25px"/>
            </tree>
        `,
        groupBy: ["int_field"],
    });
    expect(`.o_resize`).toHaveCount(8);
    expect(Math.floor(queryRect(`th[data-name="bar"]`).width)).toBe(70);
    expect(Math.floor(queryRect(`th[data-name="int_field"]`).width)).toBe(74);
    expect(Math.floor(queryRect(`th[data-name="qux"]`).width)).toBe(92);
    expect(Math.floor(queryRect(`th[data-name="date"]`).width)).toBe(92);
    expect(Math.floor(queryRect(`th[data-name="datetime"]`).width)).toBe(146);
    expect(Math.floor(queryRect(`th[data-name="amount"]`).width)).toBe(104);
    expect(`th[data-name="foo"]`).toHaveAttribute("style", /width: 100%/);
    expect(Math.floor(queryRect(`th[data-name="currency_id"]`).width)).toBe(25);
});

test(`column width should depend on the widget`, async () => {
    Foo._records = []; // the width heuristic only applies when there are no records

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <tree editable="top">
                <field name="datetime" widget="date"/>
                <field name="text"/>
            </tree>
        `,
    });
    expect(Math.floor(queryRect(`th[data-name="datetime"]`).width)).toBe(92);
});

test(`column widths are kept when adding first record`, async () => {
    Foo._records = []; // in this scenario, we start with no records

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <tree editable="top">
                <field name="datetime"/>
                <field name="text"/>
            </tree>
        `,
    });
    const width = Math.floor(queryRect(`th[data-name="datetime"]`).width);

    await contains(`.o_list_button_add`).click();
    expect(`.o_data_row`).toHaveCount(1);
    expect(Math.floor(queryRect(`th[data-name="datetime"]`).width)).toBe(width);
});

test(`column widths are kept when editing a record`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <tree editable="bottom">
                <field name="datetime"/>
                <field name="text"/>
            </tree>
        `,
    });
    const width = Math.floor(queryRect(`th[data-name="datetime"]`).width);

    await contains(`.o_data_row:eq(0) > .o_data_cell:eq(1)`).click();
    expect(`.o_selected_row`).toHaveCount(1);

    const longVal =
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " +
        "Sed blandit, justo nec tincidunt feugiat, mi justo suscipit libero, sit amet tempus " +
        "ipsum purus bibendum est.";
    await contains(`.o_field_widget[name=text] .o_input`).edit(longVal, { confirm: false });
    await contains(`.o_list_button_save`).click();
    expect(`.o_selected_row`).toHaveCount(0);
    expect(Math.floor(queryRect(`th[data-name="datetime"]`).width)).toBe(width);
});

test(`column widths are kept when switching records in edition`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <tree editable="bottom">
                <field name="m2o"/>
                <field name="text"/>
            </tree>
        `,
    });
    const width = Math.floor(queryRect(`th[data-name="m2o"]`).width);

    await contains(`.o_data_row:eq(0) > .o_data_cell:eq(1)`).click();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
    expect(Math.floor(queryRect(`th[data-name="m2o"]`).width)).toBe(width);

    await contains(`.o_data_row:eq(1) > .o_data_cell:eq(1)`).click();
    expect(`.o_data_row:eq(1)`).toHaveClass("o_selected_row");
    expect(Math.floor(queryRect(`th[data-name="m2o"]`).width)).toBe(width);
});

test.todo(`column widths are re-computed on window resize`, async () => {
    Foo._records[0].text =
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " +
        "Sed blandit, justo nec tincidunt feugiat, mi justo suscipit libero, sit amet tempus " +
        "ipsum purus bibendum est.";

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <tree editable="bottom">
                <field name="datetime"/>
                <field name="text"/>
            </tree>
        `,
    });
    const initialTextWidth = queryRect(`th[data-name="text"]`).width;
    const selectorWidth = queryRect(`th.o_list_record_selector:eq(0)`).width;

    resize({ width: queryRect(getFixture()).width / 2 });
    await animationFrame();
    const postResizeTextWidth = queryRect(`th[data-name="text"]`).width;
    const postResizeSelectorWidth = queryRect(`th.o_list_record_selector:eq(0)`).width;
    expect(postResizeTextWidth).toBeLessThan(initialTextWidth);
    expect(selectorWidth).toBe(postResizeSelectorWidth);
});

test(`columns with an absolute width are never narrower than that width`, async () => {
    Foo._records[0].text =
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit, " +
        "sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim " +
        "veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo " +
        "consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum " +
        "dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, " +
        "sunt in culpa qui officia deserunt mollit anim id est laborum";

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <tree editable="bottom">
                <field name="datetime"/>
                <field name="int_field" width="200px"/>
                <field name="text"/>
            </tree>
        `,
    });
    const width = queryRect(`th[data-name="int_field"]`).width;
    expect(Math.floor(width)).toBe(200);
});

test(`list view with data: text columns are not crushed`, async () => {
    const longText =
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do " +
        "eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim " +
        "veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo " +
        "consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum " +
        "dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, " +
        "sunt in culpa qui officia deserunt mollit anim id est laborum";

    Foo._records[0].foo = longText;
    Foo._records[0].text = longText;
    Foo._records[1].foo = "short text";
    Foo._records[1].text = "short text";
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<tree><field name="foo"/><field name="text"/></tree>`,
    });
    const fooWidth = Math.ceil(queryRect(`th[data-name="foo"]`).width);
    const textWidth = Math.ceil(queryRect(`th[data-name="text"]`).width);
    expect(fooWidth).toBe(textWidth, {
        message: "both columns should have been given the same width",
    });

    const firstRowHeight = queryRect(`.o_data_row:eq(0)`).height;
    const secondRowHeight = queryRect(`.o_data_row:eq(1)`).height;
    expect(firstRowHeight).toBeGreaterThan(secondRowHeight, {
        message:
            "in the first row, the (long) text field should be properly displayed on several lines",
    });
});

test(`button in a list view with a default relative width`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <tree>
                <field name="foo"/>
                <button name="the_button" icon="fa-heart" width="0.1"/>
            </tree>
        `,
    });
    expect(`.o_data_cell button:eq(0)`).not.toHaveAttribute("style", /width/, {
        message: "width attribute should not change the CSS style",
    });
});

test(`button columns in a list view don't have a max width`, async () => {
    // set a long foo value s.t. the column can be squeezed
    Foo._records[0].foo = "Lorem ipsum dolor sit amet";

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <tree>
                <field name="foo"/>
                <button name="b1" string="Do This"/>
                <button name="b2" string="Do That"/>
                <button name="b3" string="Or Rather Do Something Else"/>
            </tree>
        `,
    });

    // simulate a window resize (buttons column width should not be squeezed)
    resize({ width: 300 });
    await animationFrame();
    expect(`th:eq(1)`).toHaveStyle(
        { maxWidth: "92px" },
        {
            message: "max-width should be set on column foo to the minimum column width (92px)",
        }
    );
    expect(`th:eq(2)`).toHaveStyle(
        { maxWidth: "none" },
        {
            message: "no max-width should be harcoded on the buttons column",
        }
    );
});

test(`column width should not change when switching mode`, async () => {
    // Warning: this test is css dependant
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <tree editable="top">
                <field name="foo"/>
                <field name="int_field" readonly="1"/>
                <field name="m2o"/>
                <field name="m2m" widget="many2many_tags"/>
            </tree>
        `,
    });
    const startWidths = queryAllProperties(`thead th`, "offsetWidth");
    const startWidth = queryRect(`table`).width;

    // start edition of first row
    await contains(`td:not(.o_list_record_selector)`).click();
    const editionWidths = queryAllProperties(`thead th`, "offsetWidth");
    const editionWidth = queryRect(`table`).width;

    // leave edition
    await contains(`.o_list_button_save`).click();
    const readonlyWidths = queryAllProperties(`thead th`, "offsetWidth");
    const readonlyWidth = queryRect(`table`).width;
    expect(editionWidth).toBe(startWidth, {
        message: "table should have kept the same width when switching from readonly to edit mode",
    });
    expect(editionWidths).toEqual(startWidths, {
        message:
            "width of columns should remain unchanged when switching from readonly to edit mode",
    });
    expect(readonlyWidth).toBe(editionWidth, {
        message: "table should have kept the same width when switching from edit to readonly mode",
    });
    expect(readonlyWidths).toEqual(editionWidths, {
        message:
            "width of columns should remain unchanged when switching from edit to readonly mode",
    });
});

test(`column widths are kept when editing multiple records`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <tree multi_edit="1">
                <field name="datetime"/>
                <field name="text"/>
            </tree>
        `,
    });
    const width = queryRect(`th[data-name="datetime"]`).width;

    // select two records and edit
    await contains(`.o_data_row:eq(0) .o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(1) .o_list_record_selector input`).click();
    await contains(`.o_data_row:eq(0) .o_data_cell:eq(1)`).click();
    expect(`.o_selected_row`).toHaveCount(1);

    const longVal =
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed blandit, " +
        "justo nec tincidunt feugiat, mi justo suscipit libero, sit amet tempus ipsum purus " +
        "bibendum est.";
    await contains(`.o_field_widget[name=text] textarea`).edit(longVal);
    expect(`.modal`).toHaveCount(1);

    await contains(`.modal .btn-primary`).click();
    expect(`.o_selected_row`).toHaveCount(0);
    expect(`th[data-name="datetime"]`).toHaveRect({ width });
});

test(`row height and width should not change when switching mode`, async () => {
    // Warning: this test is css dependant
    serverState.multiLang = true;

    Foo._fields.foo = fields.Char({ translate: true });
    Foo._fields.boolean = fields.Boolean();

    // the width is hardcoded to make sure we have the same condition
    // between debug mode and non debug mode
    resize({ width: 1200 });
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `
            <tree editable="top">
                <field name="foo" required="1"/>
                <field name="int_field" readonly="1"/>
                <field name="boolean"/>
                <field name="date"/>
                <field name="text"/>
                <field name="amount"/>
                <field name="currency_id" column_invisible="1"/>
                <field name="m2o"/>
                <field name="m2m" widget="many2many_tags"/>
            </tree>
        `,
    });
    const startHeight = queryRect(`.o_data_row:eq(0)`).height;
    const startWidth = queryRect(`.o_data_row:eq(0)`).width;

    // start edition of first row
    await contains(`.o_data_row > td:not(.o_list_record_selector)`).click();
    expect(`.o_data_row:eq(0)`).toHaveClass("o_selected_row");
    const editionHeight = queryRect(`.o_data_row:eq(0)`).height;
    const editionWidth = queryRect(`.o_data_row:eq(0)`).width;

    // leave edition
    await contains(`.o_list_button_save`).click();
    const readonlyHeight = queryRect(`.o_data_row:eq(0)`).height;
    const readonlyWidth = queryRect(`.o_data_row:eq(0)`).width;
    expect(startHeight).toBe(editionHeight);
    expect(startHeight).toBe(readonlyHeight);
    expect(startWidth).toBe(editionWidth);
    expect(startWidth).toBe(readonlyWidth);
});

test(`editable list: list view in an initially unselected notebook page`, async () => {
    Foo._fields.o2m = fields.One2many({ relation: "abc" });
    Foo._records = [{ id: 1, o2m: [1] }];

    class Abc extends models.Model {
        titi = fields.Char();
        grosminet = fields.Char();

        _records = [
            {
                id: 1,
                titi: "Tiny text",
                grosminet:
                    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " +
                    "Ut at nisi congue, facilisis neque nec, pulvinar nunc. " +
                    "Vivamus ac lectus velit.",
            },
        ];
    }
    defineModels([Abc]);

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <notebook>
                        <page string="Page1"></page>
                        <page string="Page2">
                            <field name="o2m">
                                <tree editable="bottom">
                                    <field name="titi"/>
                                    <field name="grosminet"/>
                                </tree>
                            </field>
                        </page>
                    </notebook>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_field_one2many`).toHaveCount(0);

    await contains(`.nav-item:eq(-1) .nav-link`).click();
    expect(`.o_field_one2many`).toHaveCount(1);
    expect(queryRect(`.tab-pane:eq(-1) th:eq(0)`).width).toBeGreaterThan(80);
    expect(queryRect(`.tab-pane:eq(-1) th:eq(1)`).width).toBeGreaterThan(500);
});

test(`editable list: list view hidden by an invisible modifier`, async () => {
    Foo._fields.o2m = fields.One2many({ relation: "abc" });
    Foo._records = [{ id: 1, bar: true, o2m: [1] }];
    class Abc extends models.Model {
        titi = fields.Char();
        grosminet = fields.Char();

        _records = [
            {
                id: 1,
                titi: "Tiny text",
                grosminet:
                    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " +
                    "Ut at nisi congue, facilisis neque nec, pulvinar nunc. " +
                    "Vivamus ac lectus velit.",
            },
        ];
    }
    defineModels([Abc]);

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="bar"/>
                    <field name="o2m" invisible="bar">
                        <tree editable="bottom">
                            <field name="titi"/>
                            <field name="grosminet"/>
                        </tree>
                    </field>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_field_one2many`).toHaveCount(0);

    await contains(`.o_field_boolean input`).click();
    expect(`.o_field_one2many`).toHaveCount(1);
    expect(queryRect(`th:eq(0)`).width).toBeGreaterThan(80);
    expect(queryRect(`th:eq(1)`).width).toBeGreaterThan(700);
});

test(`editable list: updating list state while invisible`, async () => {
    Foo._onChanges = {
        bar(record) {
            record.o2m = [[5], [0, null, { display_name: "Whatever" }]];
        },
    };

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="bar"/>
                    <notebook>
                        <page string="Page 1"></page>
                        <page string="Page 2">
                            <field name="o2m">
                                <tree editable="bottom">
                                    <field name="display_name"/>
                                </tree>
                            </field>
                        </page>
                    </notebook>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_field_one2many`).toHaveCount(0);

    await contains(`.o_field_boolean input`).click();
    expect(`.o_field_one2many`).toHaveCount(0);

    await contains(`.nav-item:eq(-1) .nav-link`).click();
    expect(`.o_field_one2many`).toHaveCount(1);
    expect(`.o_field_one2many .o_data_row:eq(0)`).toHaveText("Whatever");
    expect(`th:eq(0)`).toHaveAttribute("style", /width: /);
});
